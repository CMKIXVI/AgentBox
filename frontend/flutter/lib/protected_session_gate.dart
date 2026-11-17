import 'package:material_ui/material_ui.dart';

import 'auth_session.dart';

/// A fail-closed presentation gate for routes that require an authenticated
/// session. The application must provide an OIDC-backed [sessionReader].
///
/// This widget does not perform login, refresh credentials, or grant backend
/// permissions. The backend remains authoritative for every API operation.
class AgentBoxProtectedSessionGate extends StatefulWidget {
  const AgentBoxProtectedSessionGate({
    required this.sessionReader,
    required this.authenticatedBuilder,
    required this.unauthenticatedBuilder,
    super.key,
  });

  final AgentBoxSessionReader sessionReader;
  final Widget Function(BuildContext, AgentBoxSession) authenticatedBuilder;
  final WidgetBuilder unauthenticatedBuilder;

  @override
  State<AgentBoxProtectedSessionGate> createState() =>
      _AgentBoxProtectedSessionGateState();
}

class _AgentBoxProtectedSessionGateState
    extends State<AgentBoxProtectedSessionGate> {
  late Future<AgentBoxSession?> _sessionFuture;

  @override
  void initState() {
    super.initState();
    _sessionFuture = widget.sessionReader.readSession();
  }

  @override
  void didUpdateWidget(covariant AgentBoxProtectedSessionGate oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.sessionReader != widget.sessionReader) {
      _sessionFuture = widget.sessionReader.readSession();
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<AgentBoxSession?>(
      future: _sessionFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final session = snapshot.data;
        if (snapshot.hasError || !isUsableAgentBoxSession(session)) {
          return widget.unauthenticatedBuilder(context);
        }
        return widget.authenticatedBuilder(context, session!);
      },
    );
  }
}
