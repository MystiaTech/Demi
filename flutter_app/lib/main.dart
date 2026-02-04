import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import 'screens/chat_screen.dart';
import 'providers/chat_provider.dart';

void main() {
  runApp(const DemiApp());
}

class DemiApp extends StatelessWidget {
  const DemiApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ChatProvider()),
      ],
      child: MaterialApp(
        title: 'Demi Chat',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF6c5ce7),
            brightness: Brightness.light,
          ),
          textTheme: GoogleFonts.robotoTextTheme(),
        ),
        darkTheme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF6c5ce7),
            brightness: Brightness.dark,
          ),
          textTheme: GoogleFonts.robotoTextTheme(
            ThemeData(brightness: Brightness.dark).textTheme,
          ),
        ),
        themeMode: ThemeMode.dark,
        home: const ChatScreen(),
      ),
    );
  }
}
