import 'package:agentbox/auth_session.dart';
import 'package:agentbox/session_gate.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';

class FixedSessionReader implements AgentBoxSessionReader {
  FixedSessionReader(this.session, {this.error});
  final AgentBoxSession? session;
  final Object? error;

  @override
  Future<AgentBoxSession?> readSession() async {
    if (error != null) throw error!;
    return session;
  }
}

void main() {
  final validSession = AgentBoxSession(
    subject: 'user-1',
    accessToken: 'short-lived-token',
    expiresAt: DateTime.now().add(const Duration(minutes: 5)),
  );

  Widget gate(FixedSessionReader reader) => MaterialApp(
        home: AgentBoxSessionGate(
          sessionReader: reader,
          loadingBuilder: (_) => const Text('Loading session'),
          unauthenticatedBuilder: (_) => const Text('Sign-in required'),
          authenticatedBuilder: (_, session) => Text('Welcome ${session.subject}'),
        ),
      );

  testWidgets('renders protected child for a valid session', (tester) async {
    await tester.pumpWidget(gate(FixedSessionReader(validSession)));
    await tester.pumpAndSettle();
    expect(find.text('Welcome user-1'), findsOneWidget);
  });

  testWidgets('fails closed for missing session', (tester) async {
    await tester.pumpWidget(gate(FixedSessionReader(null)));
    await tester.pumpAndSettle();
    expect(find.text('Sign-in required'), findsOneWidget);
  });

  testWidgets('fails closed for expired session', (tester) async {
    final expired = AgentBoxSession(
      subject: 'user-1',
      accessToken: 'expired-token',
      expiresAt: DateTime.now().subtract(const Duration(seconds: 1)),
    );
    await tester.pumpWidget(gate(FixedSessionReader(expired)));
    await tester.pumpAndSettle();
    expect(find.text('Sign-in required'), findsOneWidget);
  });

  testWidgets('fails closed when session reader throws', (tester) async {
    await tester.pumpWidget(gate(FixedSessionReader(null, error: Exception('offline'))));
    await tester.pumpAndSettle();
    expect(find.text('Sign-in required'), findsOneWidget);
  });

  testWidgets('rechecks and closes protected UI at the expiry safety boundary', (tester) async {
    final nearExpiry = AgentBoxSession(
      subject: 'user-1',
      accessToken: 'short-lived-token',
      expiresAt: DateTime.now().add(const Duration(seconds: 31)),
    );
    await tester.pumpWidget(gate(FixedSessionReader(nearExpiry)));
    await tester.pump();
    expect(find.text('Welcome user-1'), findsOneWidget);

    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();
    expect(find.text('Sign-in required'), findsOneWidget);
  });
}
