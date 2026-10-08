import 'package:flutter/material.dart';
import '../models/models.dart';

class AppProvider with ChangeNotifier {
  int _selectedNavIndex = 0;
  String _selectedDarshanCategory = 'All';
  String _gitaSearchQuery = '';

  int get selectedNavIndex => _selectedNavIndex;
  String get selectedDarshanCategory => _selectedDarshanCategory;
  String get gitaSearchQuery => _gitaSearchQuery;

  void setNavIndex(int index) {
    _selectedNavIndex = index;
    notifyListeners();
  }

  void setDarshanCategory(String category) {
    _selectedDarshanCategory = category;
    notifyListeners();
  }

  void setGitaSearchQuery(String query) {
    _gitaSearchQuery = query;
    notifyListeners();
  }

  // Live Temple Darshans Data
  final List<DarshanItem> _darshans = [
    DarshanItem(
      id: '1',
      templeName: 'Shree Bankey Bihari Ji',
      location: 'Vrindavan, Uttar Pradesh',
      imageUrl: 'https://images.unsplash.com/photo-1609342122563-a43ac8917a3a?q=80&w=1000&auto=format&fit=crop',
      date: 'Today • Morning Shringaar',
      category: 'Vrindavan',
    ),
    DarshanItem(
      id: '2',
      templeName: 'Dwarkadhish Temple',
      location: 'Dwarka, Gujarat',
      imageUrl: 'https://images.unsplash.com/photo-1582510003544-4d00b7f74220?q=80&w=1000&auto=format&fit=crop',
      date: 'Today • Rajbhog Aarti',
      category: 'Dwarka',
    ),
    DarshanItem(
      id: '3',
      templeName: 'ISKCON Mayapur Chandrodaya',
      location: 'Mayapur, West Bengal',
      imageUrl: 'https://images.unsplash.com/photo-1542382257-80dedb725088?q=80&w=1000&auto=format&fit=crop',
      date: 'Yesterday • Mangala Aarti',
      category: 'Mayapur',
    ),
  ];

  List<DarshanItem> get darshans {
    if (_selectedDarshanCategory == 'All') return _darshans;
    return _darshans.where((d) => d.category == _selectedDarshanCategory).toList();
  }

  void toggleDarshanFavorite(String id) {
    final index = _darshans.indexWhere((item) => item.id == id);
    if (index != -1) {
      _darshans[index].isFavorite = !_darshans[index].isFavorite;
      notifyListeners();
    }
  }

  // Live Bhagavad Gita Verses
  final List<GitaVerse> _gitaVerses = [
    GitaVerse(
      chapter: 2,
      verse: 47,
      sanskrit: 'कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।\nमा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि॥',
      translation: 'You have a right to perform your prescribed duty, but you are not entitled to the fruits of action.',
      explanation: 'Focus completely on doing your work with devotion, detachment, and care, rather than anxiety over outcome.',
    ),
    GitaVerse(
      chapter: 9,
      verse: 22,
      sanskrit: 'अनन्याश्चिन्तयन्तो मां ये जनाः पर्युपासते।\nतेषां नित्याभियुक्तानां योगक्षेमं वहाम्यहम्॥',
      translation: 'To those who worship Me with exclusive devotion, I carry what they lack and preserve what they have.',
      explanation: 'Complete trust in the Divine brings peace, protection, and fulfillment in all aspects of life.',
    ),
  ];

  List<GitaVerse> get filteredGitaVerses {
    if (_gitaSearchQuery.isEmpty) return _gitaVerses;
    return _gitaVerses.where((v) {
      return v.translation.toLowerCase().contains(_gitaSearchQuery.toLowerCase()) ||
          v.sanskrit.contains(_gitaSearchQuery) ||
          'chapter ${v.chapter}'.contains(_gitaSearchQuery.toLowerCase());
    }).toList();
  }

  void toggleGitaBookmark(int chapter, int verse) {
    final index = _gitaVerses.indexWhere((v) => v.chapter == chapter && v.verse == verse);
    if (index != -1) {
      _gitaVerses[index].isBookmarked = !_gitaVerses[index].isBookmarked;
      notifyListeners();
    }
  }
}