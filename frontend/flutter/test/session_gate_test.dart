import 'dart:async';

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

class DeferredSessionReader implements AgentBoxSessionReader {
  final Completer<AgentBoxSession?> completer = Completer<AgentBoxSession?>();

  @override
  Future<AgentBoxSession?> readSession() => completer.future;
}

void main() {
  final validSession = AgentBoxSession(
    subject: 'user-1',
    accessToken: 'short-lived-token',
    expiresAt: DateTime.now().add(const Duration(minutes: 5)),
  );

  Widget gate(AgentBoxSessionReader reader, {DateTime Function()? clock}) =>
      MaterialApp(
        home: AgentBoxSessionGate(
          sessionReader: reader,
          loadingBuilder: (_) => const Text('Loading session'),
          clock: clock,
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
    await tester.pumpWidget(
      gate(FixedSessionReader(null, error: Exception('offline'))),
    );
    await tester.pumpAndSettle();
    expect(find.text('Sign-in required'), findsOneWidget);
  });

  testWidgets('rechecks and closes protected UI at the expiry safety boundary', (
    tester,
  ) async {
    var now = DateTime.now();
    final nearExpiry = AgentBoxSession(
      subject: 'user-1',
      accessToken: 'short-lived-token',
      expiresAt: now.add(const Duration(seconds: 31)),
    );
    await tester.pumpWidget(
      gate(FixedSessionReader(nearExpiry), clock: () => now),
    );
    await tester.pump();
    expect(find.text('Welcome user-1'), findsOneWidget);

    now = now.add(const Duration(seconds: 2));
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();
    expect(find.text('Sign-in required'), findsOneWidget);
  });

  testWidgets('ignores an older reader result after reader replacement', (
    tester,
  ) async {
    final oldReader = DeferredSessionReader();
    final replacementSession = AgentBoxSession(
      subject: 'replacement-user',
      accessToken: 'replacement-token',
      expiresAt: DateTime.now().add(const Duration(minutes: 5)),
    );

    await tester.pumpWidget(gate(oldReader));
    await tester.pump();
    expect(find.text('Loading session'), findsOneWidget);

    await tester.pumpWidget(gate(FixedSessionReader(replacementSession)));
    await tester.pumpAndSettle();
    expect(find.text('Welcome replacement-user'), findsOneWidget);

    oldReader.completer.complete(validSession);
    await tester.pump();
    expect(find.text('Welcome replacement-user'), findsOneWidget);
    expect(find.text('Welcome user-1'), findsNothing);
  });

  testWidgets('ignores an older reader error after reader replacement', (
    tester,
  ) async {
    final oldReader = DeferredSessionReader();
    final replacementSession = AgentBoxSession(
      subject: 'replacement-user',
      accessToken: 'replacement-token',
      expiresAt: DateTime.now().add(const Duration(minutes: 5)),
    );

    await tester.pumpWidget(gate(oldReader));
    await tester.pump();
    await tester.pumpWidget(gate(FixedSessionReader(replacementSession)));
    await tester.pumpAndSettle();

    oldReader.completer.completeError(Exception('stale reader failure'));
    await tester.pump();
    expect(find.text('Welcome replacement-user'), findsOneWidget);
    expect(find.text('Sign-in required'), findsNothing);
  });
}
