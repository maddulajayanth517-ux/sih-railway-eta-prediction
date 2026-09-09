import 'package:flutter/material.dart';

import '../services/train_tracker_service.dart';
import '../widgets/ETACard.dart';

class LiveStatus extends StatefulWidget {
	const LiveStatus({super.key, this.service});
	final TrainTrackerService? service;

	@override
	State<LiveStatus> createState() => _LiveStatusState();
}

class _LiveStatusState extends State<LiveStatus> {
	late final TrainTrackerService _service;
	TrainState? _train;
	Object? _error;
	bool _isRefreshing = false;

	@override
	void initState() {
		super.initState();
		_service = widget.service ?? TrainTrackerService.demo();
		_service.states.listen((state) {
			if (mounted) setState(() => _train = state);
		}, onError: (Object error) {
			if (mounted) setState(() => _error = error);
		});
		_service.start();
	}

	@override
	void dispose() {
		_service.dispose();
		super.dispose();
	}

	Future<void> _refresh() async {
		setState(() => _isRefreshing = true);
		await _service.refresh();
		if (mounted) setState(() => _isRefreshing = false);
	}

	@override
	Widget build(BuildContext context) {
		final train = _train;
		return Scaffold(
			appBar: AppBar(
				backgroundColor: Colors.transparent,
				titleSpacing: 20,
				title: const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
					Text('RAILWISE', style: TextStyle(fontSize: 12, letterSpacing: 2.4, fontWeight: FontWeight.w800)),
					Text('Live journey', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
				]),
				actions: [IconButton(onPressed: _refresh, tooltip: 'Refresh train status', icon: const Icon(Icons.refresh_rounded)), const SizedBox(width: 12)],
			),
			body: RefreshIndicator(
				onRefresh: _refresh,
				child: ListView(padding: const EdgeInsets.fromLTRB(20, 8, 20, 32), children: [
					if (_isRefreshing) const LinearProgressIndicator(minHeight: 2),
					if (_error != null) Padding(padding: const EdgeInsets.only(bottom: 12), child: Text('Unable to update: $_error', style: const TextStyle(color: Colors.red))),
					if (train == null)
						const SizedBox(height: 420, child: Center(child: CircularProgressIndicator()))
					else ...[
						Text(train.trainName, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
						const SizedBox(height: 4),
						Text('Train ${train.trainId}  |  Running live', style: TextStyle(color: Colors.grey.shade700)),
						const SizedBox(height: 16),
						ETACard(train: train),
						const SizedBox(height: 16),
						_LiveMap(train: train),
						const SizedBox(height: 16),
						_Panel(title: 'Journey details', child: Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: [
							_Metric(icon: Icons.speed_rounded, value: '${train.currentSpeed.toStringAsFixed(0)} km/h', label: 'Current speed'),
							_Metric(icon: Icons.shield_outlined, value: '${(train.confidenceScore * 100).toStringAsFixed(0)}%', label: 'Confidence'),
							_Metric(icon: Icons.schedule_rounded, value: '${train.predictedDelayMinutes} min', label: 'Delay'),
						])),
						const SizedBox(height: 16),
						_Panel(title: 'Why the delay?', child: Column(children: train.delayReasons.map((reason) => ListTile(contentPadding: EdgeInsets.zero, dense: true, leading: const Icon(Icons.info_outline_rounded, color: Color(0xFFD36B32)), title: Text(reason, style: const TextStyle(fontSize: 13))).toList())),
						const SizedBox(height: 18),
						Text('Updated ${train.updatedLabel}', textAlign: TextAlign.center, style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
					],
				]),
			),
		);
	}
}

class _LiveMap extends StatelessWidget {
	const _LiveMap({required this.train});
	final TrainState train;
	@override
	Widget build(BuildContext context) => Container(height: 164, clipBehavior: Clip.antiAlias, decoration: BoxDecoration(color: const Color(0xFFDCEAE0), borderRadius: BorderRadius.circular(20)), child: Stack(children: [
				CustomPaint(size: Size.infinite, painter: _MapPainter()),
				Positioned(left: 24, top: 20, child: _MapLabel(code: train.lastStationCode, label: 'Last station')),
				Positioned(right: 22, bottom: 20, child: _MapLabel(code: train.nextStationCode, label: 'Next station')),
				Center(child: Container(padding: const EdgeInsets.all(10), decoration: const BoxDecoration(color: Color(0xFF0E6655), shape: BoxShape.circle), child: const Icon(Icons.train_rounded, color: Colors.white, size: 22))),
				Positioned(top: 14, right: 14, child: DecoratedBox(decoration: BoxDecoration(color: Colors.white.withOpacity(.85), borderRadius: BorderRadius.circular(8)), child: const Padding(padding: EdgeInsets.symmetric(horizontal: 9, vertical: 6), child: Text('LIVE', style: TextStyle(color: Color(0xFF0E6655), fontWeight: FontWeight.w800, fontSize: 11)))),
			]));
}

class _MapLabel extends StatelessWidget {
	const _MapLabel({required this.code, required this.label});
	final String code;
	final String label;
	@override
	Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(code, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)), Text(label, style: const TextStyle(fontSize: 11))]);
}

class _MapPainter extends CustomPainter {
	@override
	void paint(Canvas canvas, Size size) {
		final paint = Paint()..color = const Color(0xFF6D9D80)..strokeWidth = 3..style = PaintingStyle.stroke;
		final path = Path()..moveTo(0, size.height * .72)..quadraticBezierTo(size.width * .28, size.height * .12, size.width * .53, size.height * .56)..quadraticBezierTo(size.width * .76, size.height * .92, size.width, size.height * .28);
		canvas.drawPath(path, paint);
		final dash = Paint()..color = const Color(0xFF9BC2A9)..strokeWidth = 1;
		for (var y = 30.0; y < size.height; y += 32) canvas.drawLine(0, y, size.width, y, dash);
	}
	@override
	bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _Panel extends StatelessWidget {
	const _Panel({required this.title, required this.child});
	final String title;
	final Widget child;
	@override
	Widget build(BuildContext context) => Container(padding: const EdgeInsets.all(18), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20), boxShadow: [BoxShadow(color: Colors.black.withOpacity(.04), blurRadius: 18, offset: const Offset(0, 5))]), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)), const SizedBox(height: 14), child]);
}

class _Metric extends StatelessWidget {
	const _Metric({required this.icon, required this.value, required this.label});
	final IconData icon;
	final String value;
	final String label;
	@override
	Widget build(BuildContext context) => Column(children: [Icon(icon, color: const Color(0xFF0E6655), size: 22), const SizedBox(height: 6), Text(value, style: const TextStyle(fontWeight: FontWeight.w800)), const SizedBox(height: 2), Text(label, style: TextStyle(color: Colors.grey.shade600, fontSize: 11))]);
}
