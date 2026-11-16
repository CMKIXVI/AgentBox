import 'dart:convert';

import 'package:agentbox/agentbox_api.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('health is public and does not request an access token', () async {
    var tokenRequested = false;
    final client = AgentBoxApiClient(
      baseUrl: 'https://api.example.test',
      accessTokenProvider: () async {
        tokenRequested = true;
        return null;
      },
      httpClient: MockClient((request) async {
        expect(request.url.path, '/health');
        expect(request.headers.containsKey('authorization'), isFalse);
        return http.Response(jsonEncode({'status': 'ok', 'service': 'agentbox-api'}), 200);
      }),
    );

    final result = await client.health();
    expect(result['status'], 'ok');
    expect(tokenRequested, isFalse);
    client.close();
  });

  test('protected calls attach bearer token and never send tenant headers', () async {
    final client = AgentBoxApiClient(
      baseUrl: 'https://api.example.test',
      accessTokenProvider: () async => 'short-lived-access-token',
      httpClient: MockClient((request) async {
        expect(request.headers['authorization'], 'Bearer short-lived-access-token');
        expect(request.headers.containsKey('x-tenant-id'), isFalse);
        expect(request.url.path, '/v1/agents/demo/versions');
        return http.Response(
          jsonEncode({'agent_id': 'demo', 'items': [], 'limit': 50, 'offset': 0}),
          200,
        );
      }),
    );

    final result = await client.listAgentVersions('demo');
    expect(result['agent_id'], 'demo');
    client.close();
  });

  test('missing access token fails before making a request', () async {
    final client = AgentBoxApiClient(
      baseUrl: 'https://api.example.test',
      accessTokenProvider: () async => null,
      httpClient: MockClient((request) async {
        fail('A request must not be sent without an access token');
      }),
    );

    await expectLater(
      client.listAgentVersions('demo'),
      throwsA(isA<AgentBoxApiException>().having((error) => error.statusCode, 'statusCode', 401)),
    );
    client.close();
  });
  test('durable execution job transport binds idempotency and lifecycle routes', () async {
    final seen = <String>[];
    final client = AgentBoxApiClient(
      baseUrl: 'https://api.example.test',
      accessTokenProvider: () async => 'short-lived-access-token',
      httpClient: MockClient((request) async {
        seen.add('${request.method} ${request.url.path}');
        expect(request.headers['authorization'], 'Bearer short-lived-access-token');
        if (request.url.path.endsWith('/jobs')) {
          expect(request.method, 'POST');
          expect(request.headers['idempotency-key'], 'job-key-001');
          expect(jsonDecode(request.body), {
            'input': {'prompt': 'hello'},
            'max_output_tokens': 512,
          });
          return http.Response(jsonEncode({'job_id': 'job-001', 'state': 'queued'}), 202);
        }
        if (request.url.path.endsWith('/events')) {
          return http.Response(jsonEncode({'items': []}), 200);
        }
        if (request.url.path.endsWith('/cancel')) {
          expect(request.method, 'POST');
          return http.Response(jsonEncode({'job_id': 'job-001', 'state': 'cancel_requested'}), 200);
        }
        return http.Response(jsonEncode({'job_id': 'job-001', 'state': 'queued'}), 200);
      }),
    );

    final submitted = await client.submitExecutionJob(
      agentId: 'demo-agent',
      version: '1.0.0',
      input: {'prompt': 'hello'},
      maxOutputTokens: 512,
      idempotencyKey: 'job-key-001',
    );
    expect(submitted['state'], 'queued');
    expect((await client.getExecutionJob('job-001'))['job_id'], 'job-001');
    expect((await client.listExecutionJobEvents('job-001'))['items'], isEmpty);
    expect((await client.cancelExecutionJob('job-001'))['state'], 'cancel_requested');
    expect(seen, [
      'POST /v1/agents/demo-agent/versions/1.0.0/jobs',
      'GET /v1/execution-jobs/job-001',
      'GET /v1/execution-jobs/job-001/events',
      'POST /v1/execution-jobs/job-001/cancel',
    ]);
    client.close();
  });

}
