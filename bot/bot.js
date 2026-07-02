// Bot is an ES Module because Puppeteer v25 is ESM-only
import puppeteer from "puppeteer";
import { createWriteStream, writeFileSync, mkdirSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { spawn } from "child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));

const args = process.argv.slice(2);
const meetUrl = args[0];
const outputAudio = args[1] || "meeting_audio.webm";
const outputParticipants = args[2] || "participants.json";
const durationSeconds = parseInt(args[3] || "60");

// Screenshot dir for debugging
const screenshotDir = join(__dirname, "..", "app", "uploads", "bot_screenshots");
mkdirSync(screenshotDir, { recursive: true });

async function screenshot(page, name) {
    try {
        const p = join(screenshotDir, `${name}.png`);
        await page.screenshot({ path: p, fullPage: false });
        console.log(`[BOT] Screenshot saved: ${p}`);
    } catch (e) {
        console.log(`[BOT] Screenshot failed (${name}):`, e.message);
    }
}

if (!meetUrl) {
    console.error("Usage: node bot.js <meet_url> <output_audio> <output_json> <duration_sec>");
    process.exit(1);
}

async function startBot() {
    console.log(`[BOT] Starting bot for ${meetUrl}`);

    // --- Set up a virtual PulseAudio sink so we can capture Chrome's audio ---
    // This creates an isolated virtual speaker; Chrome audio routes there, ffmpeg records from it.
    const SINK_NAME = "meettrack_bot_sink";
    let virtualSinkModule = null;

    try {
        const { execSync } = await import("child_process");
        // Load a null sink (virtual speaker) into PulseAudio
        const moduleId = execSync(
            `pactl load-module module-null-sink sink_name=${SINK_NAME} sink_properties=device.description=MeetTrackBot`
        ).toString().trim();
        virtualSinkModule = moduleId;
        console.log(`[BOT] Virtual PulseAudio sink created (module ${moduleId}).`);
    } catch (e) {
        console.log(`[BOT] Could not create virtual sink (PulseAudio unavailable?): ${e.message}`);
        console.log(`[BOT] Falling back to default audio sink for recording.`);
    }

    // The monitor source for the virtual sink (what we record from).
    // - If virtual sink: records ONLY Chrome's audio (isolated, clean)
    // - Fallback: records default.monitor = everything playing on your speakers (includes Meet audio)
    //   NOT the mic — the mic would be just 'default' source
    const recordSource = virtualSinkModule ? `${SINK_NAME}.monitor` : "default.monitor";

    const chromePath = await puppeteer.executablePath();
    console.log(`[BOT] Using Chrome at: ${chromePath}`);

    const browser = await puppeteer.launch({
        executablePath: chromePath,
        headless: false,   // Must be visible — Google's bot detection blocks headless Chrome at join
        defaultViewport: null,
        env: {
            ...process.env,
            // Route Chrome audio output to our virtual sink (PulseAudio/PipeWire compatible)
            ...(virtualSinkModule ? { PULSE_SINK: SINK_NAME } : {}),
        },
        args: [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream",
            "--disable-features=IsolateOrigins",
            "--disable-site-isolation-trials",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--lang=en-US",
            "--window-size=1280,800",
        ]
    });

    const page = await browser.newPage();

    // Spoof user agent to look like a real Chrome browser
    await page.setUserAgent(
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    );

    // Hide webdriver property
    await page.evaluateOnNewDocument(() => {
        Object.defineProperty(navigator, "webdriver", { get: () => undefined });
        window.chrome = { runtime: {} };
    });

    // Grant mic/camera permissions
    const context = browser.defaultBrowserContext();
    await context.overridePermissions('https://meet.google.com', ['microphone', 'camera']);

    console.log("[BOT] Navigating to Google Meet...");
    try {
        await page.goto(meetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await new Promise(r => setTimeout(r, 4000));
        console.log("[BOT] Page loaded. URL:", page.url());
        await screenshot(page, "01_page_loaded");
    } catch (e) {
        console.error("[BOT] Failed to load Google Meet page:", e.message);
        await screenshot(page, "01_load_error");
        await browser.close();
        process.exit(1);
    }

    const title = await page.title();
    const currentUrl = page.url();
    console.log(`[BOT] Page title: "${title}" | URL: ${currentUrl}`);

    if (currentUrl.includes("accounts.google.com")) {
        console.error("[BOT] BLOCKED: Redirected to Google Sign-In.");
        await screenshot(page, "02_signin_redirect");
        await browser.close();
        process.exit(1);
    }

    // --- Find and fill name input ---
    const nameSelectors = [
        'input[type="text"]',
        'input[aria-label*="name" i]',
        'input[placeholder*="name" i]',
    ];

    let typedName = false;
    for (const sel of nameSelectors) {
        try {
            await page.waitForSelector(sel, { timeout: 3000 });
            await page.click(sel);
            await page.evaluate(sel => { document.querySelector(sel).value = ''; }, sel);
            await page.type(sel, "MeetTrack AI", { delay: 50 });
            console.log(`[BOT] Typed name using selector: ${sel}`);
            typedName = true;
            break;
        } catch (e) { }
    }

    if (!typedName) {
        console.log("[BOT] Could not find name input. Will attempt to join directly.");
    }

    await screenshot(page, "02_before_join_click");

    // Dismiss "Sign in with your Google account" popup
    try {
        const dismissed = await page.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const gotItBtn = buttons.find(b => b.innerText?.trim() === 'Got it');
            if (gotItBtn) { gotItBtn.click(); return true; }
            return false;
        });
        if (dismissed) {
            console.log('[BOT] Dismissed "Sign in" popup.');
            await new Promise(r => setTimeout(r, 800));
        }
    } catch (e) { }

    await new Promise(r => setTimeout(r, 1000));

    // Click Join / Ask to join
    const joinClicked = await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const joinBtn = buttons.find(b => {
            const text = (b.innerText || '').toLowerCase();
            const label = (b.getAttribute('aria-label') || '').toLowerCase();
            return text.includes('ask to join') || text.includes('join now') ||
                text.includes('join') || label.includes('join');
        });
        if (joinBtn) { joinBtn.click(); return joinBtn.innerText || 'clicked'; }
        return null;
    });

    if (joinClicked) {
        console.log(`[BOT] Clicked join button: "${joinClicked.trim()}". Waiting for page to stabilize...`);
        await new Promise(r => setTimeout(r, 4000));
    } else {
        console.log("[BOT] No join button found.");
    }

    await screenshot(page, "03_after_join_click");

    // Wait until inside the meeting (mic/camera controls appear)
    console.log("[BOT] Waiting to be admitted (up to 2 minutes)...");
    try {
        await page.waitForFunction(() => {
            const selectors = [
                'button[aria-label*="microphone" i]',
                'button[aria-label*="camera" i]',
                'button[aria-label*="Turn off microphone" i]',
                'button[aria-label*="Turn on microphone" i]',
                'button[data-is-muted]',
                '[jsname="BOHaEe"]',
            ];
            return selectors.some(sel => document.querySelectorAll(sel).length > 0);
        }, { timeout: 120000 });
        console.log("[BOT] Joined the meeting successfully!");
        await screenshot(page, "04_inside_meeting");
    } catch (e) {
        console.error("[BOT] Timed out waiting to be admitted.");
        await screenshot(page, "04_admission_timeout");
        await browser.close();
        if (virtualSinkModule) {
            try { execSync(`pactl unload-module ${virtualSinkModule}`); } catch (_) { }
        }
        process.exit(1);
    }

    // --- Start audio recording with ffmpeg ---
    console.log(`[BOT] Starting ffmpeg audio recording from source: ${recordSource}`);
    const ffmpegProc = spawn("ffmpeg", [
        "-y",
        "-f", "pulse",
        "-i", recordSource,
        "-c:a", "libopus",
        "-b:a", "96k",
        outputAudio
    ]);

    ffmpegProc.stderr.on("data", (d) => {
        // ffmpeg logs to stderr by default; only print errors
        const line = d.toString();
        if (line.includes("Error") || line.includes("error")) {
            console.log("[FFMPEG]", line.trim());
        }
    });

    ffmpegProc.on("exit", (code) => {
        console.log(`[BOT] ffmpeg exited with code ${code}`);
    });

    console.log(`[BOT] Recording audio to: ${outputAudio}`);

    // Try to open the participants panel
    try {
        const opened = await page.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const btn = buttons.find(b => {
                const label = (b.getAttribute('aria-label') || '').toLowerCase();
                return label.includes('people') || label.includes('participant');
            });
            if (btn) { btn.click(); return true; }
            return false;
        });
        if (opened) console.log("[BOT] Opened participants sidebar.");
        else console.log("[BOT] Could not find participants button.");
        await new Promise(r => setTimeout(r, 1500));
        await screenshot(page, "05_participants_panel");
    } catch (e) {
        console.log("[BOT] Error opening participants:", e.message);
    }

    const participants = new Set();

    // Scrape participants every 5 seconds
    const scrapeInterval = setInterval(async () => {
        try {
            const names = await page.evaluate(() => {
                const elements = document.querySelectorAll('[role="listitem"] span[dir="auto"], [role="listitem"] div[dir="auto"]');
                return Array.from(elements)
                    .map(e => e.innerText?.trim())
                    .filter(n => n && n !== "You" && !n.includes("Presentation"));
            });
            names.forEach(n => participants.add(n));
            writeFileSync(outputParticipants, JSON.stringify(Array.from(participants), null, 2));
            if (names.length > 0) {
                console.log(`[BOT] Current participants: ${Array.from(participants).join(", ")}`);
            }
        } catch (e) { }
    }, 5000);

    // Record for the specified duration
    console.log(`[BOT] Recording for ${durationSeconds} seconds...`);
    await new Promise(r => setTimeout(r, durationSeconds * 1000));

    console.log("[BOT] Recording complete. Stopping ffmpeg...");
    clearInterval(scrapeInterval);

    // Stop ffmpeg gracefully
    ffmpegProc.stdin.write("q");
    await new Promise(r => setTimeout(r, 2000));
    ffmpegProc.kill("SIGTERM");

    try {
        await browser.close();
    } catch (e) {
        console.log("[BOT] Browser close warning (safe to ignore):", e.message);
    }

    // Unload virtual sink
    if (virtualSinkModule) {
        try {
            const { execSync } = await import("child_process");
            execSync(`pactl unload-module ${virtualSinkModule}`);
            console.log("[BOT] Removed virtual PulseAudio sink.");
        } catch (e) { }
    }

    console.log("[BOT] Done. Audio saved to:", outputAudio);
    console.log("[BOT] Participants saved to:", outputParticipants);
}

startBot().catch(err => {
    console.error("[BOT] Fatal Error:", err.message);
    console.error(err.stack);
    process.exit(1);
});
