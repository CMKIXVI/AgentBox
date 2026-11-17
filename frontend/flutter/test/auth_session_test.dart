import 'package:agentbox/auth_session.dart';
import 'package:flutter_test/flutter_test.dart';
class FakeSessionReader implements AgentBoxSessionReader {
  FakeSessionReader(this.session);
  final AgentBoxSession? session;
  @override
  Future<AgentBoxSession?> readSession() async => session;
}
void main() {
  final now = DateTime.utc(2026, 11, 13, 12);
  test('returns valid access token', () async {
    final provider = createAccessTokenProvider(FakeSessionReader(AgentBoxSession(
      subject: 'user-1', accessToken: 'access-token', expiresAt: now.add(const Duration(minutes: 5)),
    )), clock: () => now);
    expect(await provider(), 'access-token');
  });
  test('fails closed without a session', () async {
    final provider = createAccessTokenProvider(FakeSessionReader(null), clock: () => now);
    expect(await provider(), isNull);
  });
  test('rejects expired and near-expiry sessions', () async {
    for (final expiry in [now.subtract(const Duration(seconds: 1)), now.add(const Duration(seconds: 30))]) {
      final provider = createAccessTokenProvider(FakeSessionReader(AgentBoxSession(
        subject: 'user-1', accessToken: 'access-token', expiresAt: expiry,
      )), clock: () => now);
      expect(await provider(), isNull);
    }
  });
  test('rejects empty subject and token', () async {
    final emptySubject = createAccessTokenProvider(FakeSessionReader(AgentBoxSession(
      subject: '', accessToken: 'token', expiresAt: now.add(const Duration(minutes: 5)),
    )), clock: () => now);
    final emptyToken = createAccessTokenProvider(FakeSessionReader(AgentBoxSession(
      subject: 'user-1', accessToken: '', expiresAt: now.add(const Duration(minutes: 5)),
    )), clock: () => now);
    expect(await emptySubject(), isNull);
    expect(await emptyToken(), isNull);
  });
}
