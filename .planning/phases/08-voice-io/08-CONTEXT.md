# Phase 08: Voice I/O - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement speech-to-text (STT) and text-to-speech (TTS) for voice communication with Demi. Voice becomes an additional input/output channel alongside existing text-based Discord and Android interfaces. All processing must be local (no external APIs) to maintain autonomy and privacy.
</domain>

<decisions>
## Implementation Decisions

### Voice Activation
- Always listening with wake word detection ("Hey Demi")
- When idle or preparing to ramble: Demi actively listens for any speech
- Privacy protection: Only processes speech when wake word detected or in ramble mode
- Visual indicator when actively processing speech

### Voice Synthesis  
- Clear articulation as baseline characteristic
- Tone inflection varies based on emotional state
- Emotional intensity changes through tone, not pitch/speed variation
- Consistent voice signature maintained across all emotions

### Integration Points
- Parallel mode with existing text input
- Both voice and text inputs active simultaneously
- Voice input sends immediately on confident recognition
- Users can switch between typing and speaking freely

### Error Handling
- Automatic retry up to 3 times on failed recognition
- In-character error responses reflecting personality
- Reacts to sudden background noises (curiosity/concern)
- Ignores subtle ambient noise (fans, distant traffic)

### Performance Targets
- Local-only processing (no external STT/TTS APIs)
- Prioritize accuracy and latency balance based on 12GB RAM constraint
- Fast enough for natural conversation flow

### Claude's Discretion
- Choice of wake word implementation
- Background noise detection thresholds
- STT confidence thresholds for immediate vs retry behavior
- Visual/audio feedback design for listening state

</decisions>

<specifics>
## Specific Ideas

- Wake word: "Hey Demi" with consistent activation
- Voice errors: "Bless your heart for trying, but you're mumble" or "Speak up, mortal"
- Sudden noises: Door slams, glass breaking → "What was that? Everything okay?"
- Performance: Balance Whisper STT with pyttsx3 TTS for local accuracy
- Visual indicator: Microphone icon or pulse when listening

</specifics>

<deferred>
## Deferred Ideas

- Voice training/customization - Phase for advanced personalization
- Multiple voice profiles - Would require user preference system
- Voice biometrics - Separate security concern
- Voice commands beyond wake word - Additional automation complexity

</deferred>

---

*Phase: 08-voice-io*
*Context gathered: 2026-02-03*