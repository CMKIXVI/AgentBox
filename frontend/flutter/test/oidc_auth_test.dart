import 'package:flutter_test/flutter_test.dart';
import 'package:agentbox/oidc_auth.dart';

void main() {
  group('AgentBoxOidcConfig', () {
    test('requires issuer, client ID, and redirect URI', () {
      const incomplete = AgentBoxOidcConfig(
        issuer: 'https://identity.example.test',
        clientId: '',
        redirectUrl: 'com.example.agentbox:/oauth2redirect',
      );
      const complete = AgentBoxOidcConfig(
        issuer: 'https://identity.example.test',
        clientId: 'agentbox-mobile',
        redirectUrl: 'com.example.agentbox:/oauth2redirect',
      );

      expect(incomplete.isConfigured, isFalse);
      expect(complete.isConfigured, isTrue);
    });

    test('rejects whitespace-only configuration values', () {
      const config = AgentBoxOidcConfig(
        issuer: ' ',
        clientId: 'mobile',
        redirectUrl: 'redirect',
      );

      expect(config.isConfigured, isFalse);
    });
  });
}
