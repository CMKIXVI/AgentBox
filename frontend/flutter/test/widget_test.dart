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
    expect(find.text('Find execution'), findsOneWidget);
  });
}
