import 'package:flutter/material.dart';
import '../core/app_styles.dart';
import '../widgets/custom_app_bar.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({Key? key}) : super(key: key);

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final TextEditingController _searchController = TextEditingController();
  bool _hasSearched = false;
  String _currentFilter = 'Any part of text';
  String _currentTypeText = 'Text';
  final List<String> _filters = ['Any part of text', 'Exact word'];
  final List<String> _typeTexts = ['Text', 'Topic'];

  // Simulated search results
  final List<Map<String, dynamic>> _searchResults = [
    {'topic': 'કામ', 'matches': 2, 'snippet': 'સંત આશ્રમમાં સંત નિવાસ...'},
    {'topic': 'લોભ', 'matches': 3, 'snippet': 'લોભથી સંત વૃત્તિ નષ્ટ...'},
    {'topic': 'ક્રોધ', 'matches': 8, 'snippet': 'ક્રોધાવેશમાં સંત ભાવના...'},
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.backgroundLight,
      appBar: CustomAppBar(
        title: 'Search Menu',
        showBackButton: true,
      ),
      body: Stack(
        children: [
          Container(height: 30, color: AppColors.primaryRed),
          Container(
            decoration: const BoxDecoration(
              color: AppColors.backgroundLight,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(30),
                topRight: Radius.circular(30),
              ),
            ),
            child: Column(
              children: [
                _buildSearchHeader(),
                Expanded(
                  child: AnimatedCrossFade(
                    duration: const Duration(milliseconds: 300),
                    firstChild: _buildEmptyStateView(),
                    secondChild: _buildResultsView(),
                    crossFadeState: _hasSearched ? CrossFadeState.showSecond : CrossFadeState.showFirst,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchHeader() {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 0),
      color: AppColors.backgroundLight,
      child: Column(
        children: [
          _buildSearchField(),
          const SizedBox(height: 15),
          Row(
            children: [
              _buildDropdownFilter(_currentFilter, _filters, (v) => setState(() => _currentFilter = v)),
              const SizedBox(width: 15),
              _buildDropdownFilter(_currentTypeText, _typeTexts, (v) => setState(() => _currentTypeText = v)),
            ],
          ),
          const SizedBox(height: 15),
          _buildResultCountBar(),
        ],
      ),
    );
  }

  Widget _buildSearchField() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        color: AppColors.tileBackground,
        borderRadius: BorderRadius.circular(30),
        border: Border.all(color: Colors.black12),
      ),
      child: TextField(
        controller: _searchController,
        style: AppStyles.titleText,
        decoration: InputDecoration(
          hintText: 'Search...',
          border: InputBorder.none,
          prefixIcon: Icon(Icons.search, color: AppColors.textLight),
        ),
        onSubmitted: (query) {
          if (query.isNotEmpty) {
            setState(() {
              _hasSearched = true;
            });
          }
        },
      ),
    );
  }

  Widget _buildDropdownFilter(String value, List<String> items, Function(String) onChanged) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 15),
        decoration: BoxDecoration(
          color: AppColors.tileBackground,
          borderRadius: BorderRadius.circular(25),
          border: Border.all(color: Colors.black12),
        ),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<String>(
            value: value,
            icon: Icon(Icons.expand_more, color: AppColors.textLight),
            isExpanded: true,
            style: AppStyles.titleText.copyWith(fontSize: 15, fontWeight: FontWeight.normal),
            items: items.map((String value) {
              return DropdownMenuItem<String>(
                value: value,
                child: Text(value),
              );
            }).toList(),
            onChanged: (String? newValue) {
              if (newValue != null) onChanged(newValue);
            },
          ),
        ),
      ),
    );
  }

  Widget _buildResultCountBar() {
    String countText = _hasSearched ? 'Showing 6 results from 13 Vaktavyam' : 'Showing 0 results from 0 Vaktavyam';
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 20),
      color: AppColors.accentGold,
      child: Text(countText, style: AppStyles.bodyText.copyWith(fontWeight: FontWeight.bold), textAlign: TextAlign.center),
    );
  }

  Widget _buildEmptyStateView() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.search, size: 80, color: AppColors.textLight.withOpacity(0.3)),
        const SizedBox(height: 20),
        Text('Records not found', style: AppStyles.header2.copyWith(color: AppColors.textLight.withOpacity(0.6))),
      ],
    );
  }

  Widget _buildResultsView() {
    return ListView.separated(
      padding: const EdgeInsets.all(20),
      itemCount: _searchResults.length,
      separatorBuilder: (context, index) => const SizedBox(height: 15),
      itemBuilder: (context, index) {
        final result = _searchResults[index];
        return _buildSearchResultCard(result);
      },
    );
  }

  Widget _buildSearchResultCard(Map<String, dynamic> result) {
    String query = _searchController.text;
    String fullText = result['snippet'];
    List<TextSpan> spans = [];
    int start = 0;
    while ((start = fullText.toLowerCase().indexOf(query.toLowerCase(), start)) != -1) {
      // Add text before the match
      spans.add(TextSpan(text: fullText.substring(spans.isNotEmpty ? fullText.indexOf(spans.last.text!) + spans.last.text!.length : 0, start)));
      // Add the match (highlighted)
      spans.add(TextSpan(
          text: fullText.substring(start, start + query.length), style: const TextStyle(backgroundColor: AppColors.accentGold, fontWeight: FontWeight.bold)));
      start += query.length;
    }
    // Add text after the last match
    spans.add(TextSpan(text: fullText.substring(start)));

    return Container(
      decoration: BoxDecoration(
        color: AppColors.tileBackground,
        borderRadius: BorderRadius.circular(25),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.05), spreadRadius: 1, blurRadius: 5, offset: const Offset(0, 2)),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(result['topic'], style: AppStyles.titleText.copyWith(fontWeight: FontWeight.bold)),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: const BoxDecoration(color: AppColors.accentGold, shape: BoxShape.circle),
                  child: Text(result['matches'].toString(), style: AppStyles.bodyText.copyWith(fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            const SizedBox(height: 15),
            RichText(
              text: TextSpan(
                  style: AppStyles.bodyText.copyWith(color: AppColors.textLight.withOpacity(0.5)),
                  children: spans),
            ),
          ],
        ),
      ),
    );
  }
}