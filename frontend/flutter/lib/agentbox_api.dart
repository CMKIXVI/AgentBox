import 'dart:convert';

import 'package:http/http.dart' as http;

typedef AccessTokenProvider = Future<String?> Function();

class AgentBoxApiException implements Exception {
  const AgentBoxApiException(this.statusCode, this.detail);

  final int statusCode;
  final Object? detail;

  @override
  String toString() => 'AgentBox API request failed ($statusCode): $detail';
}

class AgentBoxApiClient {
  AgentBoxApiClient({
    required String baseUrl,
    required AccessTokenProvider accessTokenProvider,
    http.Client? httpClient,
  })  : _baseUri = Uri.parse(baseUrl),
        _accessTokenProvider = accessTokenProvider,
        _httpClient = httpClient ?? http.Client() {
    if (_baseUri.scheme != 'https' &&
        _baseUri.host != 'localhost' &&
        _baseUri.host != '127.0.0.1') {
      throw ArgumentError('AgentBox API must use HTTPS outside localhost development');
    }
  }

  final Uri _baseUri;
  final AccessTokenProvider _accessTokenProvider;
  final http.Client _httpClient;

  Uri _uri(List<String> segments, [Map<String, String>? query]) {
    return _baseUri.replace(
      pathSegments: [..._baseUri.pathSegments.where((part) => part.isNotEmpty), ...segments],
      queryParameters: query,
    );
  }

  Future<Map<String, dynamic>> _request(
    String method,
    List<String> pathSegments, {
    Map<String, String>? query,
    Object? body,
    Map<String, String>? extraHeaders,
    bool authenticated = true,
  }) async {
    final headers = <String, String>{'Accept': 'application/json'};
    if (extraHeaders != null) headers.addAll(extraHeaders);
    if (body != null) headers['Content-Type'] = 'application/json';
    if (authenticated) {
      final token = await _accessTokenProvider();
      if (token == null || token.isEmpty) {
        throw const AgentBoxApiException(401, 'An authenticated session is required');
      }
      headers['Authorization'] = 'Bearer $token';
    }

    final uri = _uri(pathSegments, query);
    final encodedBody = body == null ? null : jsonEncode(body);
    final response = switch (method) {
      'GET' => await _httpClient.get(uri, headers: headers),
      'POST' => await _httpClient.post(uri, headers: headers, body: encodedBody),
      _ => throw ArgumentError.value(method, 'method', 'Unsupported HTTP method'),
    };

    if (response.statusCode < 200 || response.statusCode >= 300) {
      Object? detail;
      try {
        detail = jsonDecode(response.body);
      } on FormatException {
        detail = response.body;
      }
      throw AgentBoxApiException(response.statusCode, detail);
    }
    if (response.body.isEmpty) return <String, dynamic>{};
    final decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('AgentBox API returned an unexpected response shape');
    }
    return decoded;
  }

  Future<Map<String, dynamic>> health() => _request(
        'GET',
        const ['health'],
        authenticated: false,
      );

  Future<Map<String, dynamic>> listAgentVersions(
    String agentId, {
    int limit = 50,
    int offset = 0,
  }) =>
      _request(
        'GET',
        ['v1', 'agents', agentId, 'versions'],
        query: {'limit': '$limit', 'offset': '$offset'},
      );

  Future<Map<String, dynamic>> getAgentVersion(String agentId, String version) =>
      _request('GET', ['v1', 'agents', agentId, 'versions', version]);

  Future<Map<String, dynamic>> createAgent(Map<String, dynamic> manifest) =>
      _request('POST', const ['v1', 'agents'], body: {'manifest': manifest});

  Future<Map<String, dynamic>> getExecution(String executionId) =>
      _request('GET', ['v1', 'executions', executionId]);

  Future<Map<String, dynamic>> submitExecutionJob({
    required String agentId,
    required String version,
    required Object? input,
    required int maxOutputTokens,
    required String idempotencyKey,
  }) =>
      _request(
        'POST',
        ['v1', 'agents', agentId, 'versions', version, 'jobs'],
        body: {'input': input, 'max_output_tokens': maxOutputTokens},
        extraHeaders: {'Idempotency-Key': idempotencyKey},
      );

  Future<Map<String, dynamic>> getExecutionJob(String jobId) =>
      _request('GET', ['v1', 'execution-jobs', jobId]);

  Future<Map<String, dynamic>> listExecutionJobEvents(String jobId) =>
      _request('GET', ['v1', 'execution-jobs', jobId, 'events']);

  Future<Map<String, dynamic>> cancelExecutionJob(String jobId) =>
      _request('POST', ['v1', 'execution-jobs', jobId, 'cancel']);

  Future<Map<String, dynamic>> createEvaluationProfile(Map<String, dynamic> profile) =>
      _request('POST', ['v1', 'evaluation-profiles'], body: {'profile': profile});

  Future<Map<String, dynamic>> listEvaluationProfileVersions(String profileId) =>
      _request('GET', ['v1', 'evaluation-profiles', profileId, 'versions']);

  Future<Map<String, dynamic>> getEvaluationProfile(String profileId, String version) =>
      _request('GET', ['v1', 'evaluation-profiles', profileId, 'versions', version]);

  Future<Map<String, dynamic>> submitEvaluation({
    required String agentId,
    required String version,
    required String profileId,
    required String profileVersion,
    required List<dynamic> results,
  }) =>
      _request(
        'POST',
        ['v1', 'agents', agentId, 'versions', version, 'evaluations'],
        body: {
          'profile_id': profileId,
          'profile_version': profileVersion,
          'results': results,
        },
      );

  Future<Map<String, dynamic>> listEvaluations(String agentId, String version) =>
      _request('GET', ['v1', 'agents', agentId, 'versions', version, 'evaluations']);

  Future<Map<String, dynamic>> getEvaluation(String runId) =>
      _request('GET', ['v1', 'evaluations', runId]);

  Future<Map<String, dynamic>> createCognitiveRun({
    required String goalRef,
    required String agentRef,
    required String idempotencyKey,
  }) =>
      _request(
        'POST',
        const ['v1', 'cognitive-runs'],
        body: {'goal_ref': goalRef, 'agent_ref': agentRef},
        extraHeaders: {'Idempotency-Key': idempotencyKey},
      );

  Future<Map<String, dynamic>> getCognitiveRun(String runId) =>
      _request('GET', ['v1', 'cognitive-runs', runId]);

  Future<Map<String, dynamic>> listCognitiveRunEvents(
    String runId, {
    int afterSequence = 0,
    int limit = 200,
  }) =>
      _request(
        'GET',
        ['v1', 'cognitive-runs', runId, 'events'],
        query: {'after_sequence': '$afterSequence', 'limit': '$limit'},
      );

  Future<Map<String, dynamic>> assembleCognitiveContext({
    required String runId,
    required Map<String, dynamic> request,
    required String idempotencyKey,
  }) =>
      _request(
        'POST',
        ['v1', 'cognitive-runs', runId, 'context'],
        body: request,
        extraHeaders: {'Idempotency-Key': idempotencyKey},
      );

  void close() => _httpClient.close();
}
