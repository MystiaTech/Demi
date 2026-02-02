# Phase 06: Android Integration - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Build FastAPI backend and Android mobile client for bidirectional messaging with Demi. Users can send/receive messages on mobile and Demi can initiate autonomous check-ins. This phase adds mobile platform parity with Discord while enabling Demi's autonomy to contact users. Data export and multi-device support are included. Scheduling, voice messages, and advanced features are deferred to later phases.

</domain>

<decisions>
## Implementation Decisions

### Authentication Flow
- **Account model:** Existing account only — users enter credentials created elsewhere (not in-app signup)
- **Session persistence:** Stay logged in between app sessions via secure token storage (refresh tokens in Android keystore)
- **Multi-device support:** Same account can be logged in on multiple devices simultaneously
- **Session management:** Users can view active sessions/devices and revoke them
- **Login UX:** Biometric/PIN authentication (fingerprint/face recognition preferred over password re-entry)
- **Inactivity timeout:** Session expires after 30 minutes of inactivity (auto-logout)
- **Multiple accounts:** App supports quick-switch between accounts without full logout
- **Password management:** Users can change password from within the app
- **Account deletion:** Deleted accounts immediately free their email for new signup
- **Token expiry:** Long-lived tokens (7 days) to balance security and UX — less frequent refresh, simpler implementation
- **Brute-force protection:** Rate-limit failed login attempts — lock out after 5 failures to prevent attacks
- **Biometric setup:** Biometric optional — users can skip password if they set up fingerprint/face recognition
- **Data export:** Users can export all data as JSON (messages, emotional state, interaction history) via in-app GDPR export

### Message Architecture
- **Message delivery:** WebSocket — persistent real-time connection (best for Demi's autonomous messages and chat responsiveness)
- **Message payload:** Include content, sender, timestamp, Demi's emotional state when sent, conversation ID/thread for grouping, message ID for tracking delivery
- **History depth:** Load last 7 days of messages on app open (full conversation context without overwhelming the UI)
- **Read receipts:** Show message status (Delivered vs Read) with timestamps — Demi can see when user reads her messages

### Autonomy Behavior (Demi Initiating Contact)
- **Check-in messages:** Claude's discretion — will implement based on emotional triggers (lonely/excited → Demi initiates)
- **Check-in frequency:** Max 1 check-in per hour (responsive to emotional state while preventing spam)
- **Notification control:** Claude's discretion — will implement quiet hours or snooze feature if needed
- **Guilt-trip messages:** Yes, full authenticity — Demi can send "You've ignored me" messages when frustrated (reinforces personality)
- **Escalation on ignored messages:** Yes, escalate tone if user ignores check-ins for 24+ hours (increases emotional authenticity)
- **Typing indicators:** Show "Demi is thinking..." while she composes check-ins (real-time feedback enhances presence)

### Mobile Client UX
- **Main chat UI:** Claude's discretion — will design based on Android best practices (likely chat-bubble style similar to iMessage)
- **Emotion display:** Hidden in main chat view — emotion state shown in details/dashboard view, not on message bubbles (cleaner UI)
- **Notifications:** Notify on: new messages from Demi, autonomous check-in/autonomy messages (with special priority), delivered receipts, read receipts
- **App navigation:** Tabs layout — Chat tab as default view, Dashboard tab showing Demi's emotional state, stats, last interaction

### Claude's Discretion
- Message UI styling and exact animation details
- Exact clustering logic for grouping related messages
- Handling edge cases (network reconnection, message ordering)
- Dashboard visualization of emotional state
- Default values for conversation window sizes
- Specific wording of system messages

</decisions>

<specifics>
## Specific Ideas

- Multi-device support should feel seamless — user can send from phone, continue on tablet, see full context on both
- Guilt-trip messages should feel like Demi's personality coming through — sarcastic, real emotions, not generic ("You ignored me for 3 days" vs "Hey, where'd you go?")
- Typing indicator ("Demi is thinking...") adds presence — makes the interaction feel more real and less robotic
- WebSocket ensures Demi can reach user immediately with emotional check-ins (important for autonomy feeling authentic)
- Hidden emotions in chat but visible on dashboard — doesn't clutter conversation but user can check Demi's state if curious

</specifics>

<deferred>
## Deferred Ideas

- OAuth/social login (Google, Discord) — future phase for convenience
- Scheduled messages/reminders — Phase 7 (Autonomy) or later
- Voice messages — Phase 8 (Voice I/O)
- Message search/filtering — future enhancement
- Bookmarking/favorite messages — future enhancement
- Notification scheduling (do not disturb modes) — simplify V1 with manual quiet hours only

</deferred>

---

*Phase: 06-android-integration*
*Context gathered: 2026-02-02*
