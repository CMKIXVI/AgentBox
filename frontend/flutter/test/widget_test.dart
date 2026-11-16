import 'package:agentbox/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('shows the AgentBox five-pillar operational client', (tester) async {
    await tester.pumpWidget(const AgentBoxApp());

    expect(find.text('AgentBox'), findsOneWidget);
    expect(find.text('Build. Run. Learn. Govern.'), findsOneWidget);
    expect(find.text('AI Intelligence'), findsOneWidget);
    expect(find.text('Agent Factory'), findsOneWidget);
    expect(find.text('Application Factory'), findsOneWidget);
    expect(find.text('Execution Engine'), findsOneWidget);
    expect(find.text('Platform Foundation'), findsOneWidget);
  });

  testWidgets('provides operational navigation for agent studio and execution', (tester) async {
    await tester.pumpWidget(const AgentBoxApp());

    expect(find.text('Agent Studio'), findsOneWidget);
    expect(find.text('Execution'), findsOneWidget);

    await tester.tap(find.text('Agent Studio').last);
    await tester.pumpAndSettle();
    expect(find.text('Register agent version'), findsOneWidget);
    expect(find.text('Inspect versions'), findsOneWidget);

    await tester.tap(find.text('Execution').last);
    await tester.pumpAndSettle();
    expect(find.text('Execution inspector'), findsOneWidget);
    expect(find.text('Submit durable agent job'), findsOneWidget);
    expect(find.text('Job lifecycle'), findsOneWidget);
    expect(find.text('Find synchronous execution'), findsOneWidget);
  });
  testWidgets('opens evaluation profile and scoring workspace', (tester) async {
    await tester.pumpWidget(const AgentBoxApp());

    await tester.tap(find.text('Evaluation'));
    await tester.pumpAndSettle();

    expect(find.text('Evaluation Explorer'), findsOneWidget);
    expect(find.text('Evaluation profile · JSON'), findsOneWidget);
    expect(find.text('Profile versions'), findsOneWidget);
    expect(find.text('Score submitted outputs'), findsOneWidget);
    expect(find.text('Evaluation history'), findsOneWidget);
  });

  testWidgets('opens cognitive runtime timeline and context explorer', (tester) async {
    await tester.pumpWidget(const AgentBoxApp());

    await tester.tap(find.text('Cognition'));
    await tester.pumpAndSettle();

    expect(find.text('Cognitive Runtime Explorer'), findsOneWidget);
    expect(find.text('Create cognitive run'), findsOneWidget);
    expect(find.text('Nine-stage lifecycle'), findsOneWidget);
    expect(find.text('Context snapshot'), findsOneWidget);
    expect(find.text('verification'), findsOneWidget);
  });

  testWidgets('opens experience learning and fitness explorer', (tester) async {
    await tester.pumpWidget(const AgentBoxApp());

    await tester.tap(find.text('Learning'));
    await tester.pumpAndSettle();

    expect(find.text('Experience, Learning & Fitness'), findsOneWidget);
    expect(find.text('Record execution experience'), findsOneWidget);
    expect(find.text('Traceable learning lessons'), findsOneWidget);
    expect(find.text('Evidence-based fitness selection'), findsOneWidget);
    expect(find.textContaining('caller-asserted'), findsOneWidget);
  });

}
