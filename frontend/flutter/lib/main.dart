import 'package:material_ui/material_ui.dart';

import 'oidc_auth.dart';

void main() {
  runApp(const AgentBoxApp());
}

class AgentBoxApp extends StatelessWidget {
  const AgentBoxApp({super.key});

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFF527FC4);
    return MaterialApp(
      title: 'AgentBox',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: seed,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFF0B1020),
        cardTheme: const CardThemeData(
          color: Color(0xFF172238),
          margin: EdgeInsets.zero,
        ),
      ),
      home: const AgentBoxHomePage(),
    );
  }
}

class AgentBoxHomePage extends StatefulWidget {
  const AgentBoxHomePage({super.key});

  @override
  State<AgentBoxHomePage> createState() => _AgentBoxHomePageState();
}

class _AgentBoxHomePageState extends State<AgentBoxHomePage> {
  static const _oidcConfig = AgentBoxOidcConfig(
    issuer: String.fromEnvironment('AGENTBOX_OIDC_ISSUER'),
    clientId: String.fromEnvironment('AGENTBOX_OIDC_MOBILE_CLIENT_ID'),
    redirectUrl: String.fromEnvironment('AGENTBOX_OIDC_MOBILE_REDIRECT_URI'),
  );

  late final AgentBoxOidcAuth _oidcAuth = AgentBoxOidcAuth(config: _oidcConfig);
  bool _busy = false;
  bool _signedIn = false;

  Future<void> _signIn() async {
    setState(() => _busy = true);
    try {
      await _oidcAuth.signIn();
      if (!mounted) return;
      setState(() => _signedIn = true);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Authenticated with AgentBox Identity.')),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Sign-in failed: $error')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _signOut() async {
    await _oidcAuth.signOut();
    if (mounted) setState(() => _signedIn = false);
  }

  @override
  Widget build(BuildContext context) {
    final areas = [
      (
        title: 'Agent operations',
        description: 'View agents, versions, and execution status.',
        icon: Icons.hub_outlined,
      ),
      (
        title: 'Approvals',
        description: 'Review governed actions and pending decisions.',
        icon: Icons.fact_check_outlined,
      ),
      (
        title: 'Notifications',
        description: 'Stay informed about runs and platform events.',
        icon: Icons.notifications_none,
      ),
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('AgentBox'),
        actions: [
          if (_signedIn)
            IconButton(
              tooltip: 'Sign out',
              onPressed: _busy ? null : _signOut,
              icon: const Icon(Icons.logout),
            )
          else
            const Padding(
              padding: EdgeInsets.only(right: 16),
              child: Icon(Icons.account_circle_outlined),
            ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Your agent operations,\non the move.',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: 10),
            Text(
              'One AgentBox platform, with a focused cross-platform client.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            const SizedBox(height: 28),
            for (final area in areas) ...[
              Card(
                child: ListTile(
                  contentPadding: const EdgeInsets.all(16),
                  leading: Icon(area.icon, size: 28),
                  title: Text(
                    area.title,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  subtitle: Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(area.description),
                  ),
                  trailing: const Icon(Icons.chevron_right),
                ),
              ),
              const SizedBox(height: 12),
            ],
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _busy
                  ? null
                  : _signedIn
                      ? _signOut
                      : _oidcConfig.isConfigured
                          ? _signIn
                          : null,
              icon: _busy
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Icon(_signedIn ? Icons.logout : Icons.login),
              label: Text(
                _signedIn
                    ? 'Sign out'
                    : _oidcConfig.isConfigured
                        ? 'Sign in with your organization'
                        : 'OIDC configuration required',
              ),
            ),
            const SizedBox(height: 12),
            Text(
              _signedIn
                  ? 'Authenticated · Tokens are held in platform-protected storage.'
                  : 'Preview foundation · Configure OIDC issuer, mobile client ID, '
                      'and redirect URI to enable sign-in.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
