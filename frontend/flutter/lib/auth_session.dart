/// Provider-neutral boundary for a standards-compliant OIDC session adapter.
/// A selected SDK owns Authorization Code + PKCE, redirects, refresh, and
/// platform-protected storage. This file intentionally implements none of them.
class AgentBoxSession {
  const AgentBoxSession({required this.subject, required this.accessToken, required this.expiresAt, this.displayName});
  final String subject;
  final String accessToken;
  final DateTime expiresAt;
  final String? displayName;
}
abstract interface class AgentBoxSessionReader {
  Future<AgentBoxSession?> readSession();
}
typedef AgentBoxAccessTokenProvider = Future<String?> Function();
AgentBoxAccessTokenProvider createAccessTokenProvider(AgentBoxSessionReader reader, {DateTime Function()? clock}) {
  final now = clock ?? DateTime.now;
  return () async {
    final session = await reader.readSession();
    if (session == null || session.subject.isEmpty || session.accessToken.isEmpty ||
        !session.expiresAt.isAfter(now().add(const Duration(seconds: 30)))) return null;
    return session.accessToken;
  };
}
