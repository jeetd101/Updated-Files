class TempleDarshan {
  final String id;
  final String title;
  final String location;
  final String imageUrl;
  final String category;
  final String description;
  final String aartiTiming;

  TempleDarshan({
    required this.id,
    required this.title,
    required this.location,
    required this.imageUrl,
    required this.category,
    required this.description,
    required this.aartiTiming,
  });
}

class AudioTrack {
  final String id;
  final String title;
  final String artist;
  final String duration;
  final String audioUrl;
  final String category;

  AudioTrack({
    required this.id,
    required this.title,
    required this.artist,
    required this.duration,
    required this.audioUrl,
    required this.category,
  });
}

class AppData {
  static List<TempleDarshan> temples = [
    TempleDarshan(
      id: '1',
      title: 'Shree Dwarkadhish Temple',
      location: 'Dwarka, Gujarat',
      category: 'Dwarka',
      imageUrl: 'https://images.unsplash.com/photo-1627894483216-2138af692e32?q=80&w=1200&auto=format&fit=crop',
      description: 'The ancient capital of Lord Krishna, featuring sacred Jagat Mandir architecture.',
      aartiTiming: 'Mangla: 6:30 AM | Sandhya: 7:30 PM',
    ),
    TempleDarshan(
      id: '2',
      title: 'Shree Somnath Jyotirlinga',
      location: 'Veraval, Gujarat',
      category: 'Somnath',
      imageUrl: 'https://images.unsplash.com/photo-1609946506107-50500f78f697?q=80&w=1200&auto=format&fit=crop',
      description: 'The first among the 12 sacred Jyotirlinga shrines of Lord Shiva on the Arabian coast.',
      aartiTiming: 'Morning: 7:00 AM | Afternoon: 12:00 PM | Evening: 7:00 PM',
    ),
    TempleDarshan(
      id: '3',
      title: 'Ranchhodraiji Temple',
      location: 'Dakor, Gujarat',
      category: 'Dakor',
      imageUrl: 'https://images.unsplash.com/photo-1545128485-c400e7702796?q=80&w=1200&auto=format&fit=crop',
      description: 'Home to the beloved Lord Ranchhodraiji, a grand form of Lord Krishna.',
      aartiTiming: 'Mangla: 6:45 AM | Rajbhog: 12:00 PM',
    ),
    TempleDarshan(
      id: '4',
      title: 'Shree Jagannath Puri Temple',
      location: 'Puri, Odisha',
      category: 'Puri',
      imageUrl: 'https://images.unsplash.com/photo-1606293926075-69a00dbfde81?q=80&w=1200&auto=format&fit=crop',
      description: 'Sacred Dham of Lord Jagannath, Balabhadra, and Goddess Subhadra.',
      aartiTiming: 'Dwarafita: 5:00 AM | Sandhya Dhup: 7:00 PM',
    ),
    TempleDarshan(
      id: '5',
      title: 'Shree Bankey Bihari Ji',
      location: 'Vrindavan, Uttar Pradesh',
      category: 'Vrindavan',
      imageUrl: 'https://images.unsplash.com/photo-1582510003544-4d00b7f74220?q=80&w=1200&auto=format&fit=crop',
      description: 'The heart of Vrindavan devotion, famous for intimate darshans of Bihari Ji.',
      aartiTiming: 'Shringar: 8:00 AM | Shayan: 8:30 PM',
    ),
    TempleDarshan(
      id: '6',
      title: 'ISKCON Mayapur Chandrodaya',
      location: 'Mayapur, West Bengal',
      category: 'Mayapur',
      imageUrl: 'https://images.unsplash.com/photo-1561361513-2d000a50f0dc?q=80&w=1200&auto=format&fit=crop',
      description: 'Spiritual headquarters of ISKCON along the holy Ganges river.',
      aartiTiming: 'Mangala Aarti: 4:30 AM | Gaura Aarti: 6:30 PM',
    ),
  ];

  static List<AudioTrack> audioTracks = [
    AudioTrack(
      id: 'a1',
      title: 'Hare Krishna Mahamantra',
      artist: 'HG Aindra Das',
      duration: '09:40',
      category: 'Kirtan',
      audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
    ),
    AudioTrack(
      id: 'a2',
      title: 'Shree Madhurashtakam',
      artist: 'Traditional Stotram',
      duration: '04:10',
      category: 'Stotram',
      audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3',
    ),
    AudioTrack(
      id: 'a3',
      title: 'Achyutam Keshavam',
      artist: 'Devotional Bhajan',
      duration: '05:22',
      category: 'Bhajans',
      audioUrl: 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3',
    ),
  ];
}