import 'dart:convert';

import 'package:agentbox/agentbox_api.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

class FixedSessionReader implements AgentBoxSessionReader {
  FixedSessionReader(this.session);
  final AgentBoxSession? session;
  @override
  Future<AgentBoxSession?> readSession() async => session;
}

void main() {
  final sessionNow = DateTime.utc(2026, 11, 13, 12);

  test('session reader supplies bearer token and no tenant header', () async {
    final client = AgentBoxApiClient.withSessionReader(
      baseUrl: 'https://api.example.test',
      sessionReader: FixedSessionReader(AgentBoxSession(
        subject: 'user-1',
        accessToken: 'session-token',
        expiresAt: sessionNow.add(const Duration(minutes: 5)),
      )),
      clock: () => sessionNow,
      httpClient: MockClient((request) async {
        expect(request.headers['authorization'], 'Bearer session-token');
        expect(request.headers.containsKey('x-tenant-id'), isFalse);
        return http.Response(
          jsonEncode({'agent_id': 'demo', 'items': [], 'limit': 50, 'offset': 0}),
          200,
        );
      }),
    );
    await client.listAgentVersions('demo');
    client.close();
  });

  test('missing and expired sessions block requests before network access', () async {
    final sessions = <AgentBoxSession?>[
      null,
      AgentBoxSession(
        subject: 'user-1',
        accessToken: 'expired-token',
        expiresAt: sessionNow.subtract(const Duration(seconds: 1)),
      ),
    ];
    for (final session in sessions) {
      final client = AgentBoxApiClient.withSessionReader(
        baseUrl: 'https://api.example.test',
        sessionReader: FixedSessionReader(session),
        clock: () => sessionNow,
        httpClient: MockClient((request) async {
          fail('Request must not be sent without a valid session');
        }),
      );
      await expectLater(
        client.listAgentVersions('demo'),
        throwsA(isA<AgentBoxApiException>().having((error) => error.statusCode, 'statusCode', 401)),
      );
      client.close();
    }
  });

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
}
