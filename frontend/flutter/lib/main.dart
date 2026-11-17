import 'package:material_ui/material_ui.dart';

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

class AgentBoxHomePage extends StatelessWidget {
  const AgentBoxHomePage({super.key});

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
        actions: const [
          Padding(
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
            Text(
              'Preview foundation · Authentication and live API integration '
              'are not yet enabled.',
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
