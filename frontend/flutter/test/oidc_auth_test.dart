import 'package:flutter_test/flutter_test.dart';
import 'package:agentbox/oidc_auth.dart';

class FakeOidcClient implements AgentBoxOidcClient {
  AgentBoxOidcTokenResponse? signInResponse;
  AgentBoxOidcTokenResponse? refreshResponse;
  Object? refreshError;
  int signInCalls = 0;
  int refreshCalls = 0;
  String? lastRefreshToken;

  @override
  Future<AgentBoxOidcTokenResponse?> authorizeAndExchangeCode(
    AgentBoxOidcConfig config,
  ) async {
    signInCalls++;
    return signInResponse;
  }

  @override
  Future<AgentBoxOidcTokenResponse?> refresh(
    AgentBoxOidcConfig config,
    String refreshToken,
  ) async {
    refreshCalls++;
    lastRefreshToken = refreshToken;
    if (refreshError != null) throw refreshError!;
    return refreshResponse;
  }
}

class MemoryTokenStore implements AgentBoxSecureTokenStore {
  final values = <String, String>{};

  @override
  Future<String?> read(String key) async => values[key];

  @override
  Future<void> write(String key, String value) async {
    values[key] = value;
  }

  @override
  Future<void> delete(String key) async {
    values.remove(key);
  }
}

void main() {
  const config = AgentBoxOidcConfig(
    issuer: 'https://identity.example.test',
    clientId: 'agentbox-mobile',
    redirectUrl: 'com.example.agentbox:/oauth2redirect',
  );

  group('AgentBoxOidcConfig', () {
    test('requires issuer, client ID, and redirect URI', () {
      const incomplete = AgentBoxOidcConfig(
        issuer: 'https://identity.example.test',
        clientId: '',
        redirectUrl: 'com.example.agentbox:/oauth2redirect',
      );
      expect(incomplete.isConfigured, isFalse);
      expect(config.isConfigured, isTrue);
    });

    test('rejects whitespace-only configuration values', () {
      const incomplete = AgentBoxOidcConfig(
        issuer: ' ',
        clientId: 'mobile',
        redirectUrl: 'redirect',
      );
      expect(incomplete.isConfigured, isFalse);
    });
  });

  group('AgentBoxOidcAuth lifecycle', () {
    late FakeOidcClient client;
    late MemoryTokenStore store;
    late DateTime now;
    late AgentBoxOidcAuth auth;

    setUp(() {
      client = FakeOidcClient();
      store = MemoryTokenStore();
      now = DateTime.utc(2026, 11, 14, 12);
      auth = AgentBoxOidcAuth(
        config: config,
        client: client,
        secureStore: store,
        clock: () => now,
      );
    });

    test('sign-in persists access, refresh and expiry credentials', () async {
      client.signInResponse = AgentBoxOidcTokenResponse(
        accessToken: 'access-1',
        refreshToken: 'refresh-1',
        expiresAt: now.add(const Duration(minutes: 10)),
      );

      await auth.signIn();

      expect(client.signInCalls, 1);
      expect(await store.read(AgentBoxOidcAuth.accessTokenKey), 'access-1');
      expect(await store.read(AgentBoxOidcAuth.refreshTokenKey), 'refresh-1');
      expect(
        DateTime.parse((await store.read(AgentBoxOidcAuth.expiryKey))!).toUtc(),
        now.add(const Duration(minutes: 10)),
      );
    });

    test('rejects incomplete configuration before starting login', () async {
      final unconfigured = AgentBoxOidcAuth(
        config: const AgentBoxOidcConfig(
          issuer: '',
          clientId: 'mobile',
          redirectUrl: 'redirect',
        ),
        client: client,
        secureStore: store,
        clock: () => now,
      );

      expect(unconfigured.signIn(), throwsStateError);
      expect(client.signInCalls, 0);
    });

    test('returns a token that remains valid beyond refresh skew', () async {
      await store.write(AgentBoxOidcAuth.accessTokenKey, 'access-1');
      await store.write(AgentBoxOidcAuth.refreshTokenKey, 'refresh-1');
      await store.write(
        AgentBoxOidcAuth.expiryKey,
        now.add(const Duration(minutes: 5)).toIso8601String(),
      );

      expect(await auth.accessToken(), 'access-1');
      expect(client.refreshCalls, 0);
    });

    test('refreshes an expiring token and rotates refresh credential', () async {
      await store.write(AgentBoxOidcAuth.accessTokenKey, 'old-access');
      await store.write(AgentBoxOidcAuth.refreshTokenKey, 'old-refresh');
      await store.write(
        AgentBoxOidcAuth.expiryKey,
        now.add(const Duration(seconds: 30)).toIso8601String(),
      );
      client.refreshResponse = AgentBoxOidcTokenResponse(
        accessToken: 'new-access',
        refreshToken: 'new-refresh',
        expiresAt: now.add(const Duration(minutes: 10)),
      );

      expect(await auth.accessToken(), 'new-access');
      expect(client.refreshCalls, 1);
      expect(client.lastRefreshToken, 'old-refresh');
      expect(await store.read(AgentBoxOidcAuth.accessTokenKey), 'new-access');
      expect(await store.read(AgentBoxOidcAuth.refreshTokenKey), 'new-refresh');
    });

    test('fails closed and clears credentials when refresh is rejected', () async {
      await store.write(AgentBoxOidcAuth.accessTokenKey, 'old-access');
      await store.write(AgentBoxOidcAuth.refreshTokenKey, 'revoked-refresh');
      await store.write(
        AgentBoxOidcAuth.expiryKey,
        now.subtract(const Duration(minutes: 1)).toIso8601String(),
      );
      client.refreshError = StateError('refresh rejected');

      expect(await auth.accessToken(), isNull);
      expect(store.values, isEmpty);
    });

    test('clears all credentials on sign-out', () async {
      await store.write(AgentBoxOidcAuth.accessTokenKey, 'access');
      await store.write(AgentBoxOidcAuth.refreshTokenKey, 'refresh');
      await store.write(AgentBoxOidcAuth.expiryKey, now.toIso8601String());

      await auth.signOut();

      expect(store.values, isEmpty);
    });

    test('preserves refresh token when provider omits rotation', () async {
      await store.write(AgentBoxOidcAuth.accessTokenKey, 'old-access');
      await store.write(AgentBoxOidcAuth.refreshTokenKey, 'old-refresh');
      await store.write(
        AgentBoxOidcAuth.expiryKey,
        now.subtract(const Duration(seconds: 1)).toIso8601String(),
      );
      client.refreshResponse = AgentBoxOidcTokenResponse(
        accessToken: 'new-access',
        expiresAt: now.add(const Duration(minutes: 10)),
      );

      expect(await auth.accessToken(), 'new-access');
      expect(await store.read(AgentBoxOidcAuth.refreshTokenKey), 'old-refresh');
    });
  });
}
