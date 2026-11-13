# Quest Lab Online — Friend Quickstart

Quest Lab Online is a private learning game for Lazi and two friends on Windows
and Linux. There is no public matchmaking. Friends do not need Tailscale.

> **Playtest status:** These are private test builds for Lazi and two friends.
> The Linux and Windows candidates include the cloud-save capacity fix and
> passed packaged-runtime checks. The Windows candidate is installed in the
> PapaSmurff VM. The cross-device duel is the test we still need to complete;
> these are not general-release builds.

## Install and sign in

1. Install the Windows x64 or Linux x86_64 build that Lazi shares with you.
2. Open Quest Lab, create or sign in to your own account, and verify your email
   if prompted. Each person uses their own account.
3. Your campaign save and workspace stay local to your install. Joining the
   online group does not replace your campaign progress.

The desktop installer bundles Python and the packages Quest Lab needs; you do
not need to install Python, pip, Node.js, or npm just to use the game or run
Python files in its workspace. PYR's live AI features are a separate optional
setup: install [OpenCode](https://opencode.ai), open Quest Lab's terminal, run
`opencode auth login`, and sign in to a model provider. Without that setup,
the game and PvP still work, but live PYR grading and chat will be unavailable.
Provider access may require its own account or subscription.

For Windows, SmartScreen may warn that a private test build is unsigned. On
Linux, make the AppImage executable if your file manager does not offer a Run
option. The Linux build needs a recent glibc and WebKitGTK 4.1 runtime.

## Join Shax Champions House

1. Ask Lazi for a single-use group invitation. It is shown once and expires
   after 24 hours, so redeem it privately.
2. In Quest Lab, open **Online** and sign in. Under **Create or join a group**,
   paste the invitation code and choose **Join group**.
3. Open **Shax Champions House** from the left navigation, select your group,
   and choose **Enter the house**. Friends appear in the
   shared room when they are connected. Use WASD or the arrow keys to walk and
   **E** to interact.
4. Walk to the Colosseum, Leaderboards, or Sir Getrich's shop and press **E**.
   To reach the raid, follow the cyan room on the minimap's left branch to the
   far-left edge of the house; the Ferryman passage is around that side of the
   room and is not a doorway facing this camera. The buttons in the group
   panel open the Colosseum, Leaderboards, and shop directly.

The Colosseum has three duel choices:

- **Unranked** normalizes equipment for an even match.
- **Friendly** lets both players borrow from the gear catalogue.
- **Ranked** uses eligible owned equipment and updates the private group
  leaderboard.

If the app closes or loses connection during a duel, sign back in, reopen the
group's Colosseum, and choose **Resume** under **Continue a duel**. If the duel
has already expired, it returns to the normal challenge lobby. If your account
session expired, sign in again before resuming.

The co-op raid is a shared coding project: the group divides four dependent
tasks, reviews one another's work, then faces **The Choef Chief**. A completed
raid is the main way to earn **Wazi Bucks**. Colosseum duels give a smaller
amount. Sir Getrich's online shop spends Wazi Bucks; these are separate from
campaign coins.

## Host and connection

PapaSmurff must be online and connected to the internet for online play. If it
is unavailable, campaign and offline learning features remain available, but
online sign-in, the house, duels, raids, and the shop may not connect. Friends
do not need a Tailscale account or client.

If the house does not load, return to the Online page and choose **Reconnect to
the house**. If an invite has expired, ask Lazi for a new one. Do not share
account passwords or reuse another player's account.
