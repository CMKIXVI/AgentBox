import 'package:agentbox/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('shows the AgentBox operational client foundation',
      (tester) async {
    await tester.pumpWidget(const AgentBoxApp());

    expect(find.text('AgentBox'), findsOneWidget);
    expect(find.text('Agent operations'), findsOneWidget);
    expect(find.text('Approvals'), findsOneWidget);
    expect(find.text('Notifications'), findsOneWidget);
  });
}
