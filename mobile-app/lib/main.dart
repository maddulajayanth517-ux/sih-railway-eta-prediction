import 'package:flutter/material.dart';

import 'screens/LiveStatus.dart';

void main() => runApp(const RailwiseApp());

class RailwiseApp extends StatelessWidget {
	const RailwiseApp({super.key});

	@override
	Widget build(BuildContext context) => MaterialApp(
				debugShowCheckedModeBanner: false,
				title: 'Railwise',
				theme: ThemeData(
					useMaterial3: true,
					colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0E6655)),
					scaffoldBackgroundColor: const Color(0xFFF5F7F4),
				),
				home: const LiveStatus(),
			);
}
