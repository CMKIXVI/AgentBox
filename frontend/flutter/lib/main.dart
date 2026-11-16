import 'dart:convert';

import 'package:flutter/material.dart';

import 'agentbox_api.dart';
import 'oidc_auth.dart';

const _apiBaseUrl = String.fromEnvironment('AGENTBOX_API_BASE_URL');

void main() {
  runApp(const AgentBoxApp());
}

class AgentBoxApp extends StatelessWidget {
  const AgentBoxApp({super.key});

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFF78A9F5);
    return MaterialApp(
      title: 'AgentBox',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: seed,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFF0A1020),
        cardTheme: const CardThemeData(
          color: Color(0xFF17243A),
          margin: EdgeInsets.zero,
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xFF101B2D),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0xFF2A3A55)),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: Color(0xFF2A3A55)),
          ),
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
  AgentBoxApiClient? _api;
  bool _busy = false;
  bool _signedIn = false;
  int _selectedIndex = 0;
  String? _notice;
  bool _noticeIsError = false;

  final _manifestController = TextEditingController();
  final _agentIdController = TextEditingController();
  final _executionIdController = TextEditingController();
  Map<String, dynamic>? _createdAgent;
  List<dynamic> _versions = [];
  Map<String, dynamic>? _selectedVersion;
  Map<String, dynamic>? _execution;

  @override
  void initState() {
    super.initState();
    _manifestController.text = _starterManifest();
    _restoreSession();
  }

  @override
  void dispose() {
    _api?.close();
    _manifestController.dispose();
    _agentIdController.dispose();
    _executionIdController.dispose();
    super.dispose();
  }

  String _starterManifest() => const JsonEncoder.withIndent('  ').convert({
        'schema_version': '1.0.0',
        'agent_id': 'sample-support-agent',
        'version': '1.0.0',
        'name': 'Support assistant',
        'description': 'A governed support assistant agent.',
        'purpose': 'Answer support questions using approved knowledge and tools.',
        'behavior': {
          'objective': 'Provide accurate, concise support answers and ask for clarification when needed.',
          'instructions_ref': 'agentbox://instructions/support-assistant',
          'max_steps': 8,
          'timeout_seconds': 120,
        },
        'model_binding': {
          'provider_id': 'openai-compatible',
          'model_id': 'gpt-4o-mini',
        },
        'tools': <dynamic>[],
        'permissions': {
          'tool_scopes': <String>[],
          'data_scopes': <String>[],
        },
        'provenance': {
          'origin': 'authored',
          'created_at': DateTime.now().toUtc().toIso8601String(),
        },
        'runtime_targets': ['server'],
        'tags': ['starter'],
      });

  Future<void> _restoreSession() async {
    final token = await _oidcAuth.accessToken();
    if (!mounted) return;
    if (token != null && _apiBaseUrl.isNotEmpty) {
      setState(() {
        _signedIn = true;
        _api = _newApiClient();
      });
    }
  }

  AgentBoxApiClient _newApiClient() => AgentBoxApiClient(
        baseUrl: _apiBaseUrl,
        accessTokenProvider: _oidcAuth.accessToken,
      );

  void _setNotice(String message, {bool error = false}) {
    if (!mounted) return;
    setState(() {
      _notice = message;
      _noticeIsError = error;
    });
  }

  Future<void> _signIn() async {
    if (!_oidcConfig.isConfigured) {
      _setNotice('Configure the OIDC issuer, mobile client ID, and redirect URI.', error: true);
      return;
    }
    if (_apiBaseUrl.isEmpty) {
      _setNotice('Configure AGENTBOX_API_BASE_URL before signing in.', error: true);
      return;
    }
    setState(() => _busy = true);
    try {
      await _oidcAuth.signIn();
      final token = await _oidcAuth.accessToken();
      if (token == null) throw StateError('Identity provider did not establish a usable session.');
      if (!mounted) return;
      setState(() {
        _api = _newApiClient();
        _signedIn = true;
      });
      _setNotice('Signed in. AgentBox API is ready.');
    } catch (error) {
      _setNotice('Sign-in failed: $error', error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _signOut() async {
    await _oidcAuth.signOut();
    _api?.close();
    if (!mounted) return;
    setState(() {
      _api = null;
      _signedIn = false;
      _versions = [];
      _selectedVersion = null;
      _execution = null;
    });
    _setNotice('Signed out. Secure tokens were cleared.');
  }

  Future<void> _createAgent() async {
    final api = _api;
    if (!_signedIn || api == null) return;
    setState(() => _busy = true);
    try {
      final decoded = jsonDecode(_manifestController.text);
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException('Manifest must be a JSON object.');
      }
      final result = await api.createAgent(decoded);
      if (!mounted) return;
      setState(() {
        _createdAgent = result;
        _agentIdController.text = result['agent_id']?.toString() ?? '';
      });
      _setNotice('Agent version registered.');
    } catch (error) {
      _setNotice('Could not register agent: $error', error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _loadVersions() async {
    final api = _api;
    final agentId = _agentIdController.text.trim();
    if (!_signedIn || api == null || agentId.isEmpty) return;
    setState(() => _busy = true);
    try {
      final result = await api.listAgentVersions(agentId);
      final items = result['items'];
      if (!mounted) return;
      setState(() {
        _versions = items is List ? items : [];
        _selectedVersion = null;
      });
      _setNotice('Loaded ${_versions.length} version(s).');
    } catch (error) {
      _setNotice('Could not load versions: $error', error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _loadVersion(String version) async {
    final api = _api;
    if (!_signedIn || api == null) return;
    setState(() => _busy = true);
    try {
      final result = await api.getAgentVersion(_agentIdController.text.trim(), version);
      if (!mounted) return;
      setState(() => _selectedVersion = result);
    } catch (error) {
      _setNotice('Could not load version: $error', error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _loadExecution() async {
    final api = _api;
    final executionId = _executionIdController.text.trim();
    if (!_signedIn || api == null || executionId.isEmpty) return;
    setState(() => _busy = true);
    try {
      final result = await api.getExecution(executionId);
      if (!mounted) return;
      setState(() => _execution = result);
      _setNotice('Execution record loaded.');
    } catch (error) {
      _setNotice('Could not load execution: $error', error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final titles = ['Overview', 'Agent Studio', 'Execution'];
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              width: 30,
              height: 30,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary,
                borderRadius: BorderRadius.circular(9),
              ),
              child: const Text('A', style: TextStyle(color: Color(0xFF0A1020), fontWeight: FontWeight.w900)),
            ),
            const SizedBox(width: 10),
            const Text('AgentBox'),
          ],
        ),
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
        child: Column(
          children: [
            if (_notice != null)
              Container(
                width: double.infinity,
                margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: _noticeIsError ? const Color(0xFF351D27) : const Color(0xFF102B27),
                  border: Border.all(color: _noticeIsError ? const Color(0xFF76414D) : const Color(0xFF2A6959)),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(_notice!, style: TextStyle(color: _noticeIsError ? const Color(0xFFFFB2B2) : const Color(0xFF8CE0C0), fontSize: 12)),
              ),
            Expanded(
              child: IndexedStack(
                index: _selectedIndex,
                children: [
                  _buildOverview(),
                  _buildAgentStudio(),
                  _buildExecution(),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) => setState(() => _selectedIndex = index),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard_outlined), selectedIcon: Icon(Icons.dashboard), label: 'Overview'),
          NavigationDestination(icon: Icon(Icons.hub_outlined), selectedIcon: Icon(Icons.hub), label: 'Agent Studio'),
          NavigationDestination(icon: Icon(Icons.play_circle_outline), selectedIcon: Icon(Icons.play_circle), label: 'Execution'),
        ],
      ),
    );
  }

  Widget _buildOverview() {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        const Text('AGENT OPERATING ENVIRONMENT', style: TextStyle(color: Color(0xFF8BB7FF), fontSize: 10, letterSpacing: 2, fontWeight: FontWeight.w800)),
        const SizedBox(height: 12),
        Text('Build. Run. Learn. Govern.', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        Text('One AgentBox platform across your devices. The backend remains the authority for identity, permissions, and execution.', style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, height: 1.5)),
        const SizedBox(height: 24),
        _pillarCard('01', 'AI Intelligence', 'Intent, context, cognition, verification, and memory.', Icons.psychology_outlined),
        _pillarCard('02', 'Agent Factory', 'Create immutable agent manifests and inspect versions.', Icons.hub_outlined),
        _pillarCard('03', 'Application Factory', 'Compose governed capabilities and workflows.', Icons.widgets_outlined),
        _pillarCard('04', 'Execution Engine', 'Inspect execution records and operational outcomes.', Icons.play_circle_outline),
        _pillarCard('05', 'Platform Foundation', 'Identity, tenancy, authorization, audit, and persistence.', Icons.security_outlined),
        const SizedBox(height: 18),
        if (!_signedIn) ...[
          FilledButton.icon(
            onPressed: _busy ? null : _signIn,
            icon: _busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.login),
            label: Text(_oidcConfig.isConfigured ? 'Sign in with your organization' : 'Configure OIDC to sign in'),
          ),
          const SizedBox(height: 8),
          Text('API: ${_apiBaseUrl.isEmpty ? "not configured" : _apiBaseUrl}', style: const TextStyle(color: Color(0xFF91A3BE), fontSize: 11)),
        ] else
          const Chip(avatar: Icon(Icons.verified_user_outlined, size: 16), label: Text('Authenticated session')),
      ],
    );
  }

  Widget _pillarCard(String number, String title, String description, IconData icon) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 15, vertical: 7),
        leading: CircleAvatar(backgroundColor: const Color(0xFF243A59), child: Icon(icon, size: 20)),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
        subtitle: Padding(padding: const EdgeInsets.only(top: 5), child: Text(description, style: const TextStyle(fontSize: 11, height: 1.4))),
        trailing: Text(number, style: const TextStyle(color: Color(0xFF8BB7FF), fontWeight: FontWeight.w800, fontSize: 11)),
      ),
    );
  }

  Widget _buildAgentStudio() {
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        const Text('AGENT FACTORY', style: TextStyle(color: Color(0xFF8BB7FF), fontSize: 10, letterSpacing: 2, fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        Text('Agent Studio', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        const Text('Register a versioned agent or inspect an existing agent registry entry.', style: TextStyle(color: Color(0xFF9AAAC2), height: 1.5)),
        const SizedBox(height: 18),
        _sectionCard(
          title: 'Register agent version',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(controller: _manifestController, minLines: 12, maxLines: 22, style: const TextStyle(fontFamily: 'monospace', fontSize: 11), decoration: const InputDecoration(labelText: 'Agent manifest · JSON', alignLabelWithHint: true)),
              const SizedBox(height: 12),
              FilledButton(onPressed: !_signedIn || _busy ? null : _createAgent, child: Text(_busy ? 'Working…' : 'Register immutable version')),
              if (_createdAgent != null) ...[
                const SizedBox(height: 12),
                _jsonResult(_createdAgent!),
              ],
            ],
          ),
        ),
        const SizedBox(height: 14),
        _sectionCard(
          title: 'Inspect versions',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(controller: _agentIdController, decoration: const InputDecoration(labelText: 'Agent ID', hintText: 'sample-support-agent')),
              const SizedBox(height: 10),
              OutlinedButton(onPressed: !_signedIn || _busy ? null : _loadVersions, child: const Text('Load versions')),
              if (_versions.isNotEmpty) ...[
                const SizedBox(height: 8),
                for (final item in _versions)
                  if (item is Map<String, dynamic>)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('Version ${item['version'] ?? 'unknown'}'),
                      subtitle: Text(item['artifact_id']?.toString() ?? ''),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: _busy ? null : () => _loadVersion(item['version'].toString()),
                    ),
              ],
              if (_selectedVersion != null) ...[
                const SizedBox(height: 10),
                _jsonResult(_selectedVersion!),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildExecution() {
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        const Text('EXECUTION ENGINE', style: TextStyle(color: Color(0xFF8BB7FF), fontSize: 10, letterSpacing: 2, fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        Text('Execution inspector', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        const Text('Retrieve a real execution record by ID. No simulated run data is shown.', style: TextStyle(color: Color(0xFF9AAAC2), height: 1.5)),
        const SizedBox(height: 18),
        _sectionCard(
          title: 'Find execution',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(controller: _executionIdController, decoration: const InputDecoration(labelText: 'Execution ID')),
              const SizedBox(height: 10),
              FilledButton(onPressed: !_signedIn || _busy ? null : _loadExecution, child: const Text('Inspect execution')),
              if (_execution != null) ...[
                const SizedBox(height: 12),
                _jsonResult(_execution!),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _sectionCard({required String title, required Widget child}) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
            const SizedBox(height: 14),
            child,
          ],
        ),
      ),
    );
  }

  Widget _jsonResult(Map<String, dynamic> value) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: const Color(0xFF0A1220), borderRadius: BorderRadius.circular(10), border: Border.all(color: const Color(0xFF2A3A55))),
      child: SelectableText(const JsonEncoder.withIndent('  ').convert(value), style: const TextStyle(fontFamily: 'monospace', fontSize: 10, height: 1.5)),
    );
  }
}
