import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../utils/app_theme.dart';
import '../widgets/mini_player.dart';
import 'home_screen.dart';
import 'darshan_screen.dart';
import 'audio_screen.dart';
import 'gita_screen.dart';

class MainNavigationScreen extends StatelessWidget {
  const MainNavigationScreen({super.key});

  static const List<Widget> _screens = [
    HomeScreen(),
    DarshanScreen(),
    AudioScreen(),
    GitaScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final appProvider = Provider.of<AppProvider>(context);

    return Scaffold(
      body: IndexedStack(
        index: appProvider.selectedNavIndex,
        children: _screens,
      ),
      bottomNavigationBar: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const MiniPlayer(),
          BottomNavigationBar(
            currentIndex: appProvider.selectedNavIndex,
            onTap: (index) => appProvider.setNavIndex(index),
            type: BottomNavigationBarType.fixed,
            backgroundColor: AppTheme.primaryNavy,
            selectedItemColor: AppTheme.accentGold,
            unselectedItemColor: Colors.white60,
            items: const [
              BottomNavigationBarItem(
                icon: Icon(Icons.home_outlined),
                activeIcon: Icon(Icons.home),
                label: 'Home',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.temple_hindu_outlined),
                activeIcon: Icon(Icons.temple_hindu),
                label: 'Darshan',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.audiotrack_outlined),
                activeIcon: Icon(Icons.audiotrack),
                label: 'Audio',
              ),
              BottomNavigationBarItem(
                icon: Icon(Icons.menu_book_outlined),
                activeIcon: Icon(Icons.menu_book),
                label: 'Gita',
              ),
            ],
          ),
        ],
      ),
    );
  }
}