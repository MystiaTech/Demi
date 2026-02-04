// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'phoneme_data.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PhonemeFrame _$PhonemeFrameFromJson(Map<String, dynamic> json) =>
    PhonemeFrame(
      time: (json['time'] as num).toDouble(),
      viseme: json['viseme'] as String,
      weight: (json['weight'] as num?)?.toDouble() ?? 1.0,
      duration: (json['duration'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$PhonemeFrameToJson(PhonemeFrame instance) =>
    <String, dynamic>{
      'time': instance.time,
      'viseme': instance.viseme,
      'weight': instance.weight,
      'duration': instance.duration,
    };

LipSyncData _$LipSyncDataFromJson(Map<String, dynamic> json) => LipSyncData(
      audioUrl: json['audioUrl'] as String,
      phonemes: (json['phonemes'] as List<dynamic>)
          .map((e) => PhonemeFrame.fromJson(e as Map<String, dynamic>))
          .toList(),
      duration: (json['duration'] as num).toDouble(),
    );

Map<String, dynamic> _$LipSyncDataToJson(LipSyncData instance) =>
    <String, dynamic>{
      'audioUrl': instance.audioUrl,
      'phonemes': instance.phonemes,
      'duration': instance.duration,
    };
