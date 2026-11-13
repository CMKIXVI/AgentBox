import 'package:agentbox/auth_session.dart';
import 'package:agentbox/protected_session_gate.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';

class ControlledSessionReader implements AgentBoxSessionReader {
  ControlledSessionReader(this.future);
  final Future<AgentBoxSession?> future;

  @override
  Future<AgentBoxSession?> readSession() => future;
}

void main() {
  final validSession = AgentBoxSession(
    subject: 'user-1',
    accessToken: 'short-lived-token',
    expiresAt: DateTime.now().add(const Duration(minutes: 5)),
  );

  testWidgets('shows progress while session is being read', (tester) async {
    final completer = Completer<AgentBoxSession?>();
    await tester.pumpWidget(MaterialApp(
      home: AgentBoxProtectedSessionGate(
        sessionReader: ControlledSessionReader(completer.future),
        authenticatedBuilder: (_, __) => const Text('Protected content'),
        unauthenticatedBuilder: (_) => const Text('Sign in required'),
      ),
    ));
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    completer.complete(validSession);
    await tester.pumpAndSettle();
    expect(find.text('Protected content'), findsOneWidget);
  });

  testWidgets('does not render protected content without a session', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: AgentBoxProtectedSessionGate(
        sessionReader: ControlledSessionReader(Future.value(null)),
        authenticatedBuilder: (_, __) => const Text('Protected content'),
        unauthenticatedBuilder: (_) => const Text('Sign in required'),
      ),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Sign in required'), findsOneWidget);
    expect(find.text('Protected content'), findsNothing);
  });

  testWidgets('fails closed when session reader throws', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: AgentBoxProtectedSessionGate(
        sessionReader: ControlledSessionReader(
          Future.error(StateError('session unavailable')),
        ),
        authenticatedBuilder: (_, __) => const Text('Protected content'),
        unauthenticatedBuilder: (_) => const Text('Sign in required'),
      ),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Sign in required'), findsOneWidget);
    expect(find.text('Protected content'), findsNothing);
  });
}
