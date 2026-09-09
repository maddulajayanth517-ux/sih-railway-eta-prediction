import 'dart:async';
import 'dart:convert';

class TrainState {
  const TrainState({required this.trainId, required this.trainName, required this.currentLatitude, required this.currentLongitude, required this.currentSpeed, required this.lastStationCode, required this.nextStationCode, required this.scheduledArrival, required this.predictedArrival, required this.predictedDelayMinutes, required this.confidenceScore, required this.delayReasons, required this.timestamp});

  final String trainId;
  final String trainName;
  final double currentLatitude;
  final double currentLongitude;
  final double currentSpeed;
  final String lastStationCode;
  final String nextStationCode;
  final DateTime scheduledArrival;
  final DateTime predictedArrival;
  final int predictedDelayMinutes;
  final double confidenceScore;
  final List<String> delayReasons;
  final DateTime timestamp;

  factory TrainState.fromJson(Map<String, dynamic> json) => TrainState(
        trainId: json['train_id'] as String,
        trainName: json['train_name'] as String,
        currentLatitude: (json['current_latitude'] as num).toDouble(),
        currentLongitude: (json['current_longitude'] as num).toDouble(),
        currentSpeed: (json['current_speed'] as num).toDouble(),
        lastStationCode: json['last_station_code'] as String,
        nextStationCode: json['next_station_code'] as String,
        scheduledArrival: DateTime.parse(json['scheduled_arrival'] as String).toLocal(),
        predictedArrival: DateTime.parse(json['predicted_eta'] as String).toLocal(),
        predictedDelayMinutes: (json['predicted_delay_minutes'] as num).toInt(),
        confidenceScore: (json['confidence_score'] as num).toDouble(),
        delayReasons: List<String>.from(json['delay_reasons'] as List),
        timestamp: DateTime.parse(json['timestamp'] as String).toLocal(),
      );

  String get predictedArrivalLabel => _time(predictedArrival);
  String get scheduledArrivalLabel => _time(scheduledArrival);
  String get updatedLabel => '${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}';
  static String _time(DateTime date) => '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
}

typedef JsonStream = Stream<Map<String, dynamic>> Function();

class TrainTrackerService {
  TrainTrackerService({JsonStream? source}) : _source = source;
  final JsonStream? _source;
  final _controller = StreamController<TrainState>.broadcast();
  StreamSubscription<Map<String, dynamic>>? _subscription;

  factory TrainTrackerService.demo() => TrainTrackerService(source: _demoSource);
  Stream<TrainState> get states => _controller.stream;

  void start() {
    if (_source == null) return;
    _subscription = _source!().listen((payload) => _controller.add(TrainState.fromJson(payload)), onError: _controller.addError);
  }

  Future<void> refresh() async {
    if (_source == null) return;
    await _subscription?.cancel();
    start();
  }

  void dispose() {
    _subscription?.cancel();
    _controller.close();
  }

  static Stream<Map<String, dynamic>> _demoSource() async* {
    final payload = <String, dynamic>{'train_id': '12301', 'train_name': 'Howrah Rajdhani Express', 'current_latitude': 26.4499, 'current_longitude': 80.3319, 'current_speed': 78.5, 'last_station_code': 'CNB', 'next_station_code': 'PRYJ', 'scheduled_arrival': '2026-09-09T13:45:00Z', 'predicted_eta': '2026-09-09T14:10:00Z', 'predicted_delay_minutes': 25, 'confidence_score': 0.92, 'delay_reasons': ['High track density in Kanpur-Prayagraj sector', 'Preceding freight train bottleneck'], 'timestamp': '2026-09-09T11:30:00Z'};
    yield payload;
    await Future<void>.delayed(const Duration(seconds: 12));
    yield {...payload, 'current_speed': 81.2, 'timestamp': DateTime.now().toUtc().toIso8601String()};
  }
}

TrainState trainStateFromJson(String source) => TrainState.fromJson(jsonDecode(source) as Map<String, dynamic>);