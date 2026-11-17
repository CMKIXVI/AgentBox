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

  test('evaluation profile and scoring transport uses tenant-authenticated routes', () async {
    final seen = <String>[];
    final client = AgentBoxApiClient(
      baseUrl: 'https://api.example.test',
      accessTokenProvider: () async => 'short-lived-access-token',
      httpClient: MockClient((request) async {
        seen.add('${request.method} ${request.url.path}');
        expect(request.headers['authorization'], 'Bearer short-lived-access-token');
        if (request.url.path == '/v1/evaluation-profiles') {
          expect(request.method, 'POST');
          expect(jsonDecode(request.body), {
            'profile': {'profile_id': 'quality', 'version': '1.0.0'},
          });
          return http.Response(jsonEncode({'profile_id': 'quality', 'version': '1.0.0'}), 201);
        }
        if (request.url.path.endsWith('/evaluations') && request.method == 'POST') {
          expect(jsonDecode(request.body), {
            'profile_id': 'quality',
            'profile_version': '1.0.0',
            'results': [
              {'case_id': 'case-1', 'output': 'ok', 'latency_ms': 100, 'cost_usd': 0.001},
            ],
          });
          return http.Response(jsonEncode({'run_id': 'eval-001', 'passed': true}), 201);
        }
        if (request.url.path.endsWith('/versions')) {
          return http.Response(jsonEncode({'items': []}), 200);
        }
        if (request.url.path.endsWith('/evaluations')) {
          return http.Response(jsonEncode({'items': []}), 200);
        }
        return http.Response(jsonEncode({'run_id': 'eval-001', 'passed': true}), 200);
      }),
    );

    await client.createEvaluationProfile({'profile_id': 'quality', 'version': '1.0.0'});
    expect((await client.listEvaluationProfileVersions('quality'))['items'], isEmpty);
    expect((await client.getEvaluationProfile('quality', '1.0.0'))['run_id'], 'eval-001');
    final run = await client.submitEvaluation(
      agentId: 'demo-agent',
      version: '1.0.0',
      profileId: 'quality',
      profileVersion: '1.0.0',
      results: [
        {'case_id': 'case-1', 'output': 'ok', 'latency_ms': 100, 'cost_usd': 0.001},
      ],
    );
    expect(run['passed'], true);
    expect((await client.listEvaluations('demo-agent', '1.0.0'))['items'], isEmpty);
    expect((await client.getEvaluation('eval-001'))['run_id'], 'eval-001');
    expect(seen, [
      'POST /v1/evaluation-profiles',
      'GET /v1/evaluation-profiles/quality/versions',
      'GET /v1/evaluation-profiles/quality/versions/1.0.0',
      'POST /v1/agents/demo-agent/versions/1.0.0/evaluations',
      'GET /v1/agents/demo-agent/versions/1.0.0/evaluations',
      'GET /v1/evaluations/eval-001',
    ]);
    client.close();
  });

  test('cognitive runtime transport binds run, event, and context contracts', () async {
    final seen = <String>[];
    final client = AgentBoxApiClient(
      baseUrl: 'https://api.example.test',
      accessTokenProvider: () async => 'short-lived-access-token',
      httpClient: MockClient((request) async {
        seen.add('${request.method} ${request.url.path}');
        expect(request.headers['authorization'], 'Bearer short-lived-access-token');
        if (request.url.path == '/v1/cognitive-runs') {
          expect(request.headers['idempotency-key'], 'cognition-key');
          expect(jsonDecode(request.body), {
            'goal_ref': 'goal://demo',
            'agent_ref': 'demo-agent@1.0.0',
          });
          return http.Response(jsonEncode({
            'run': {'run_id': 'cog-001', 'current_stage': 'intent'},
            'initial_event': {'stage': 'intent'},
            'created': true,
          }), 201);
        }
        if (request.url.path.endsWith('/context')) {
          expect(request.headers['idempotency-key'], 'context-key');
          expect(jsonDecode(request.body), {
            'search': 'customer',
            'include_inferences': false,
            'limit': 8,
          });
          return http.Response(jsonEncode({
            'snapshot_ref': 'context-snapshot:abc',
            'snapshot': {'entities': [], 'relationships': [], 'evidence': []},
          }), 201);
        }
        if (request.url.path.endsWith('/events')) {
          expect(request.url.queryParameters['after_sequence'], '0');
          return http.Response(jsonEncode({'run_id': 'cog-001', 'items': []}), 200);
        }
        return http.Response(jsonEncode({'run_id': 'cog-001', 'status': 'active'}), 200);
      }),
    );

    final created = await client.createCognitiveRun(
      goalRef: 'goal://demo',
      agentRef: 'demo-agent@1.0.0',
      idempotencyKey: 'cognition-key',
    );
    expect((created['run'] as Map<String, dynamic>)['run_id'], 'cog-001');
    expect((await client.getCognitiveRun('cog-001'))['status'], 'active');
    expect((await client.listCognitiveRunEvents('cog-001'))['items'], isEmpty);
    final context = await client.assembleCognitiveContext(
      runId: 'cog-001',
      request: {'search': 'customer', 'include_inferences': false, 'limit': 8},
      idempotencyKey: 'context-key',
    );
    expect(context['snapshot_ref'], 'context-snapshot:abc');
    expect(seen, [
      'POST /v1/cognitive-runs',
      'GET /v1/cognitive-runs/cog-001',
      'GET /v1/cognitive-runs/cog-001/events',
      'POST /v1/cognitive-runs/cog-001/context',
    ]);
    client.close();
  });

  test('experience learning and fitness transports use tenant API contracts', () async {
    final seen = <String>[];
    final client = AgentBoxApiClient(
      baseUrl: 'https://api.example.test',
      accessTokenProvider: () async => 'short-lived-access-token',
      httpClient: MockClient((request) async {
        seen.add('${request.method} ${request.url.path}');
        expect(request.headers['authorization'], 'Bearer short-lived-access-token');
        if (request.url.path == '/v1/agent-experiences') {
          expect(jsonDecode(request.body), {
            'execution_id': 'exec-1',
            'evaluation_run_id': 'eval-1',
            'workload_ref': 'benchmark://support/v1',
            'workload_hash': 'a' * 64,
          });
          return http.Response(jsonEncode({'experience_id': 'exp-1', 'evidence_status': 'unverified'}), 201);
        }
        if (request.url.path == '/v1/agents/demo-agent/experiences') {
          return http.Response(jsonEncode({'items': [{'experience_id': 'exp-1'}]}), 200);
        }
        if (request.url.path == '/v1/agent-experiences/exp-1/lessons' && request.method == 'POST') {
          expect(jsonDecode(request.body), {
            'lesson_type': 'response.quality',
            'statement': 'Clarify missing input.',
            'evidence_refs': ['exp-1'],
            'source_kind': 'human_review',
            'extractor_version': 'agentbox-learning-ui/1.0.0',
            'confidence': 1.0,
          });
          return http.Response(jsonEncode({'lesson_id': 'lesson-1', 'status': 'proposed'}), 201);
        }
        if (request.url.path == '/v1/agent-experiences/exp-1/lessons') {
          return http.Response(jsonEncode({'items': [{'lesson_id': 'lesson-1'}]}), 200);
        }
        expect(request.url.queryParameters, {
          'profile_id': 'support-quality',
          'profile_version': '1.0.0',
          'min_samples': '3',
        });
        return http.Response(jsonEncode({'items': [{'agent_id': 'demo-agent', 'sample_count': 3}]}), 200);
      }),
    );

    final experience = await client.createExperience(
      executionId: 'exec-1',
      evaluationRunId: 'eval-1',
      workloadRef: 'benchmark://support/v1',
      workloadHash: 'a' * 64,
    );
    expect(experience['evidence_status'], 'unverified');
    expect((await client.listExperiences('demo-agent'))['items'], hasLength(1));
    final lesson = await client.createLearningLesson(
      experienceId: 'exp-1',
      lesson: {
        'lesson_type': 'response.quality',
        'statement': 'Clarify missing input.',
        'evidence_refs': ['exp-1'],
        'source_kind': 'human_review',
        'extractor_version': 'agentbox-learning-ui/1.0.0',
        'confidence': 1.0,
      },
    );
    expect(lesson['status'], 'proposed');
    expect((await client.listLearningLessons('exp-1'))['items'], hasLength(1));
    expect((await client.selectFitness(
      profileId: 'support-quality',
      profileVersion: '1.0.0',
    ))['items'], hasLength(1));
    expect(seen, [
      'POST /v1/agent-experiences',
      'GET /v1/agents/demo-agent/experiences',
      'POST /v1/agent-experiences/exp-1/lessons',
      'GET /v1/agent-experiences/exp-1/lessons',
      'GET /v1/fitness/selection',
    ]);
    client.close();
  });

  test('parent candidate experiment comparison transport', () async {
    final seen = <String>[];
    final client = AgentBoxApiClient(
      baseUrl: 'https://api.example.test',
      accessTokenProvider: () async => 'short-lived-access-token',
      httpClient: MockClient((request) async {
        seen.add('${request.method} ${request.url.path}');
        expect(request.headers['authorization'], 'Bearer short-lived-access-token');
        if (request.method == 'POST') {
          expect(jsonDecode(request.body), {
            'agent_id': 'demo-agent',
            'parent_version': '1.0.0',
            'candidate_version': '1.1.0',
            'parent_evaluation_run_id': 'parent-run',
            'candidate_evaluation_run_id': 'candidate-run',
            'workload_ref': 'benchmark://support/v1',
            'workload_hash': 'a' * 64,
          });
          return http.Response(jsonEncode({
            'comparison_id': 'comparison-1',
            'evidence_status': 'unverified',
            'promotion_eligible': false,
            'decision_authority': 'advisory_only',
          }), 201);
        }
        return http.Response(jsonEncode({
          'comparison_id': 'comparison-1',
          'evidence_status': 'unverified',
          'promotion_eligible': false,
        }), 200);
      }),
    );

    final created = await client.compareAgentExperiment(
      agentId: 'demo-agent',
      parentVersion: '1.0.0',
      candidateVersion: '1.1.0',
      parentEvaluationRunId: 'parent-run',
      candidateEvaluationRunId: 'candidate-run',
      workloadRef: 'benchmark://support/v1',
      workloadHash: 'a' * 64,
    );
    expect(created['promotion_eligible'], isFalse);
    final loaded = await client.getAgentExperimentComparison('comparison-1');
    expect(loaded['evidence_status'], 'unverified');
    expect(seen, [
      'POST /v1/agent-experiment-comparisons',
      'GET /v1/agent-experiment-comparisons/comparison-1',
    ]);
    client.close();
  });

}
