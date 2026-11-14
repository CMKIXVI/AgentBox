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

class AgentBoxOidcAuth {
  AgentBoxOidcAuth({
    required this.config,
    FlutterAppAuth? appAuth,
    FlutterSecureStorage? secureStorage,
  })  : _appAuth = appAuth ?? const FlutterAppAuth(),
        _secureStorage = secureStorage ?? const FlutterSecureStorage();

  final AgentBoxOidcConfig config;
  final FlutterAppAuth _appAuth;
  final FlutterSecureStorage _secureStorage;

  static const _accessTokenKey = 'agentbox.oidc.access_token';
  static const _refreshTokenKey = 'agentbox.oidc.refresh_token';
  static const _expiryKey = 'agentbox.oidc.access_token_expiry';

  Future<void> signIn() async {
    if (!config.isConfigured) {
      throw StateError('AgentBox OIDC client configuration is incomplete');
    }

    final response = await _appAuth.authorizeAndExchangeCode(
      AuthorizationTokenRequest(
        config.clientId,
        config.redirectUrl,
        issuer: config.issuer,
        scopes: const ['openid', 'profile', 'email', 'offline_access'],
      ),
    );

    if (response.accessToken == null) {
      throw StateError('The identity provider did not return an access token');
    }
    await _storeTokens(
      accessToken: response.accessToken!,
      refreshToken: response.refreshToken,
      expiresAt: response.accessTokenExpirationDateTime,
    );
  }

  Future<String?> accessToken() async {
    final accessToken = await _secureStorage.read(key: _accessTokenKey);
    if (accessToken == null || accessToken.isEmpty) return null;

    final expiryValue = await _secureStorage.read(key: _expiryKey);
    final expiry = expiryValue == null ? null : DateTime.tryParse(expiryValue);
    if (expiry != null && expiry.isAfter(DateTime.now().add(const Duration(minutes: 1)))) {
      return accessToken;
    }

    final refreshToken = await _secureStorage.read(key: _refreshTokenKey);
    if (refreshToken == null || refreshToken.isEmpty) {
      await signOut();
      return null;
    }

    try {
      final response = await _appAuth.token(
        TokenRequest(
          config.clientId,
          config.redirectUrl,
          issuer: config.issuer,
          refreshToken: refreshToken,
          scopes: const ['openid', 'profile', 'email', 'offline_access'],
        ),
      );
      if (response.accessToken == null) {
        await signOut();
        return null;
      }
      await _storeTokens(
        accessToken: response.accessToken!,
        refreshToken: response.refreshToken ?? refreshToken,
        expiresAt: response.accessTokenExpirationDateTime,
      );
      return response.accessToken;
    } catch (_) {
      await signOut();
      return null;
    }
  }

  Future<void> _storeTokens({
    required String accessToken,
    String? refreshToken,
    DateTime? expiresAt,
  }) async {
    await _secureStorage.write(key: _accessTokenKey, value: accessToken);
    if (refreshToken != null && refreshToken.isNotEmpty) {
      await _secureStorage.write(key: _refreshTokenKey, value: refreshToken);
    }
    if (expiresAt != null) {
      await _secureStorage.write(
        key: _expiryKey,
        value: expiresAt.toUtc().toIso8601String(),
      );
    } else {
      await _secureStorage.delete(key: _expiryKey);
    }
  }

  Future<void> signOut() async {
    await _secureStorage.delete(key: _accessTokenKey);
    await _secureStorage.delete(key: _refreshTokenKey);
    await _secureStorage.delete(key: _expiryKey);
  }
}
