import 'package:flutter_appauth/flutter_appauth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AgentBoxOidcConfig {
  const AgentBoxOidcConfig({
    required this.issuer,
    required this.clientId,
    required this.redirectUrl,
  });

  final String issuer;
  final String clientId;
  final String redirectUrl;

  bool get isConfigured =>
      issuer.trim().isNotEmpty &&
      clientId.trim().isNotEmpty &&
      redirectUrl.trim().isNotEmpty;
}

class AgentBoxOidcTokenResponse {
  const AgentBoxOidcTokenResponse({
    required this.accessToken,
    this.refreshToken,
    this.expiresAt,
  });

  final String? accessToken;
  final String? refreshToken;
  final DateTime? expiresAt;
}

/// Narrow seam around the native AppAuth plugin for deterministic lifecycle tests.
abstract interface class AgentBoxOidcClient {
  Future<AgentBoxOidcTokenResponse?> authorizeAndExchangeCode(
    AgentBoxOidcConfig config,
  );

  Future<AgentBoxOidcTokenResponse?> refresh(
    AgentBoxOidcConfig config,
    String refreshToken,
  );
}

class FlutterAppAuthOidcClient implements AgentBoxOidcClient {
  FlutterAppAuthOidcClient({FlutterAppAuth? appAuth})
      : _appAuth = appAuth ?? const FlutterAppAuth();

  final FlutterAppAuth _appAuth;

  static const _scopes = ['openid', 'profile', 'email', 'offline_access'];

  @override
  Future<AgentBoxOidcTokenResponse?> authorizeAndExchangeCode(
    AgentBoxOidcConfig config,
  ) async {
    final response = await _appAuth.authorizeAndExchangeCode(
      AuthorizationTokenRequest(
        config.clientId,
        config.redirectUrl,
        issuer: config.issuer,
        scopes: _scopes,
      ),
    );
    return _mapResponse(
      accessToken: response.accessToken,
      refreshToken: response.refreshToken,
      expiresAt: response.accessTokenExpirationDateTime,
    );
  }

  @override
  Future<AgentBoxOidcTokenResponse?> refresh(
    AgentBoxOidcConfig config,
    String refreshToken,
  ) async {
    final response = await _appAuth.token(
      TokenRequest(
        config.clientId,
        config.redirectUrl,
        issuer: config.issuer,
        refreshToken: refreshToken,
        scopes: _scopes,
      ),
    );
    return _mapResponse(
      accessToken: response.accessToken,
      refreshToken: response.refreshToken,
      expiresAt: response.accessTokenExpirationDateTime,
    );
  }

  AgentBoxOidcTokenResponse _mapResponse({
    required String? accessToken,
    required String? refreshToken,
    required DateTime? expiresAt,
  }) =>
      AgentBoxOidcTokenResponse(
        accessToken: accessToken,
        refreshToken: refreshToken,
        expiresAt: expiresAt,
      );
}

abstract interface class AgentBoxSecureTokenStore {
  Future<String?> read(String key);
  Future<void> write(String key, String value);
  Future<void> delete(String key);
}

class FlutterSecureTokenStore implements AgentBoxSecureTokenStore {
  FlutterSecureTokenStore({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  @override
  Future<String?> read(String key) => _storage.read(key: key);

  @override
  Future<void> write(String key, String value) =>
      _storage.write(key: key, value: value);

  @override
  Future<void> delete(String key) => _storage.delete(key: key);
}

class AgentBoxOidcAuth {
  AgentBoxOidcAuth({
    required this.config,
    AgentBoxOidcClient? client,
    AgentBoxSecureTokenStore? secureStore,
    DateTime Function()? clock,
  })  : _client = client ?? FlutterAppAuthOidcClient(),
        _secureStore = secureStore ?? FlutterSecureTokenStore(),
        _clock = clock ?? DateTime.now;

  final AgentBoxOidcConfig config;
  final AgentBoxOidcClient _client;
  final AgentBoxSecureTokenStore _secureStore;
  final DateTime Function() _clock;

  static const accessTokenKey = 'agentbox.oidc.access_token';
  static const refreshTokenKey = 'agentbox.oidc.refresh_token';
  static const expiryKey = 'agentbox.oidc.access_token_expiry';
  static const _refreshSkew = Duration(minutes: 1);

  Future<void> signIn() async {
    _requireConfiguration();
    final response = await _client.authorizeAndExchangeCode(config);
    final accessToken = response?.accessToken;
    if (accessToken == null || accessToken.isEmpty) {
      throw StateError('The identity provider did not return an access token');
    }
    await _storeTokens(
      accessToken: accessToken,
      refreshToken: response?.refreshToken,
      expiresAt: response?.expiresAt,
    );
  }

  Future<String?> accessToken() async {
    final accessToken = await _secureStore.read(accessTokenKey);
    if (accessToken == null || accessToken.isEmpty) return null;

    final expiryValue = await _secureStore.read(expiryKey);
    final expiry = expiryValue == null ? null : DateTime.tryParse(expiryValue);
    if (expiry != null && expiry.isAfter(_clock().add(_refreshSkew))) {
      return accessToken;
    }

    final refreshToken = await _secureStore.read(refreshTokenKey);
    if (refreshToken == null || refreshToken.isEmpty) {
      await signOut();
      return null;
    }

    try {
      _requireConfiguration();
      final response = await _client.refresh(config, refreshToken);
      final renewedAccessToken = response?.accessToken;
      if (renewedAccessToken == null || renewedAccessToken.isEmpty) {
        await signOut();
        return null;
      }
      await _storeTokens(
        accessToken: renewedAccessToken,
        refreshToken: response?.refreshToken ?? refreshToken,
        expiresAt: response?.expiresAt,
      );
      return renewedAccessToken;
    } catch (_) {
      await signOut();
      return null;
    }
  }

  void _requireConfiguration() {
    if (!config.isConfigured) {
      throw StateError('AgentBox OIDC client configuration is incomplete');
    }
  }

  Future<void> _storeTokens({
    required String accessToken,
    String? refreshToken,
    DateTime? expiresAt,
  }) async {
    await _secureStore.write(accessTokenKey, accessToken);
    if (refreshToken != null && refreshToken.isNotEmpty) {
      await _secureStore.write(refreshTokenKey, refreshToken);
    } else {
      await _secureStore.delete(refreshTokenKey);
    }
    if (expiresAt != null) {
      await _secureStore.write(expiryKey, expiresAt.toUtc().toIso8601String());
    } else {
      await _secureStore.delete(expiryKey);
    }
  }

  Future<void> signOut() async {
    await _secureStore.delete(accessTokenKey);
    await _secureStore.delete(refreshTokenKey);
    await _secureStore.delete(expiryKey);
  }
}
