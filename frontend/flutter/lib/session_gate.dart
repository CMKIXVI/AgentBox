import 'dart:async';

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
    this.clock,
    super.key,
  });

  final AgentBoxSessionReader sessionReader;
  final AgentBoxAuthenticatedBuilder authenticatedBuilder;
  final WidgetBuilder unauthenticatedBuilder;
  final WidgetBuilder loadingBuilder;
  final DateTime Function()? clock;

  @override
  State<AgentBoxSessionGate> createState() => _AgentBoxSessionGateState();
}

class _AgentBoxSessionGateState extends State<AgentBoxSessionGate> {
  AgentBoxSession? _session;
  Timer? _expiryTimer;
  bool _loading = true;
  bool _unauthenticated = false;

  @override
  void initState() {
    super.initState();
    _loadSession();
  }

  @override
  void didUpdateWidget(covariant AgentBoxSessionGate oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.sessionReader != widget.sessionReader) {
      _loadSession();
    }
  }

  DateTime get _now => widget.clock?.call() ?? DateTime.now();

  bool _isValid(AgentBoxSession? session) {
    return session != null &&
        session.subject.isNotEmpty &&
        session.accessToken.isNotEmpty &&
        session.expiresAt.isAfter(
          _now.add(const Duration(seconds: 30)),
        );
  }

  Future<void> _loadSession() async {
    _expiryTimer?.cancel();
    if (mounted) {
      setState(() {
        _loading = true;
        _session = null;
        _unauthenticated = false;
      });
    }
    try {
      final session = await widget.sessionReader.readSession();
      if (!mounted) return;
      if (!_isValid(session)) {
        setState(() {
          _loading = false;
          _unauthenticated = true;
        });
        return;
      }

      setState(() {
        _session = session;
        _loading = false;
        _unauthenticated = false;
      });

      final recheckAt = session!.expiresAt.subtract(
        const Duration(seconds: 30),
      );
      final delay = recheckAt.difference(_now);
      _expiryTimer = Timer(delay.isNegative ? Duration.zero : delay, _loadSession);
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _session = null;
        _unauthenticated = true;
      });
    }
  }

  @override
  void dispose() {
    _expiryTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return widget.loadingBuilder(context);
    if (_unauthenticated || _session == null) {
      return widget.unauthenticatedBuilder(context);
    }
    return widget.authenticatedBuilder(context, _session!);
  }
}
