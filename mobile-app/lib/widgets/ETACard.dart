import 'package:flutter/material.dart';

import '../services/train_tracker_service.dart';

class ETACard extends StatelessWidget {
  const ETACard({super.key, required this.train});
  final TrainState train;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: const Color(0xFF0E6655), borderRadius: BorderRadius.circular(22)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            const Text('ESTIMATED ARRIVAL', style: TextStyle(color: Color(0xFFBCE0C7), fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.2)),
            DecoratedBox(decoration: BoxDecoration(color: const Color(0xFF175F50), borderRadius: BorderRadius.circular(8)), child: Padding(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5), child: Text('+${train.predictedDelayMinutes} min', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12)))),
          ]),
          const SizedBox(height: 8),
          Text(train.predictedArrivalLabel, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 34)),
          Text('Scheduled ${train.scheduledArrivalLabel}', style: const TextStyle(color: Color(0xFFBCE0C7), fontSize: 13)),
        ]),
      );
}