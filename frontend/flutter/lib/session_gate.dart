import 'package:material_ui/material_ui.dart';

import 'auth_session.dart';

typedef AgentBoxAuthenticatedBuilder = Widget Function(
  BuildContext context,
  AgentBoxSession session,
);

/// UI boundary only. It does not sign users in or replace backend authorization.
class AgentBoxSessionGate extends StatefulWidget {
  const AgentBoxSessionGate({
    required this.sessionReader,
    required this.authenticatedBuilder,
    required this.unauthenticatedBuilder,
    required this.loadingBuilder,
    super.key,
  });

  final AgentBoxSessionReader sessionReader;
  final AgentBoxAuthenticatedBuilder authenticatedBuilder;
  final WidgetBuilder unauthenticatedBuilder;
  final WidgetBuilder loadingBuilder;

  @override
  State<AgentBoxSessionGate> createState() => _AgentBoxSessionGateState();
}

class _AgentBoxSessionGateState extends State<AgentBoxSessionGate> {
  late Future<AgentBoxSession?> _sessionFuture;

  @override
  void initState() {
    super.initState();
    _sessionFuture = widget.sessionReader.readSession();
  }

  @override
  void didUpdateWidget(covariant AgentBoxSessionGate oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.sessionReader != widget.sessionReader) {
      _sessionFuture = widget.sessionReader.readSession();
    }
  }

  bool _isValid(AgentBoxSession? session) {
    return session != null &&
        session.subject.isNotEmpty &&
        session.accessToken.isNotEmpty &&
        session.expiresAt.isAfter(
          DateTime.now().add(const Duration(seconds: 30)),
        );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<AgentBoxSession?>(
      future: _sessionFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return widget.loadingBuilder(context);
        }
        if (snapshot.hasError || !_isValid(snapshot.data)) {
          return widget.unauthenticatedBuilder(context);
        }
        return widget.authenticatedBuilder(context, snapshot.data!);
      },
    );
  }
}
