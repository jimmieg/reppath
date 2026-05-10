import { useState } from "react";
import Chat from "./components/Chat";
import Calendar from "./components/Calendar";
import "./App.css";

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hey! I'm RepPath, your AI training coach. Let's build your program.\n\n**What's your primary goal?**\n\n(a) Build strength · (b) Build muscle · (c) Lose fat · (d) Build endurance",
    },
  ]);
  const [plan, setPlan] = useState(null);
  const [phase, setPhase] = useState("intake");
  const [loading, setLoading] = useState(false);

  async function handleSend(userText) {
    const newMessages = [...messages, { role: "user", content: userText }];
    setMessages(newMessages);
    setLoading(true);

    try {
      const { sendMessage } = await import("./api.js");
      const result = await sendMessage(newMessages, plan);

      setMessages([
        ...newMessages,
        { role: "assistant", content: result.reply },
      ]);

      if (result.plan) setPlan(result.plan);
      if (result.phase) setPhase(result.phase);
    } catch (err) {
      setMessages([
        ...newMessages,
        {
          role: "assistant",
          content: "Something went wrong. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>RepPath</h1>
      </header>

      <main className="app-body">
        <section className="chat-panel">
          <Chat
            messages={messages}
            loading={loading}
            phase={phase}
            onSend={handleSend}
          />
        </section>

        {plan && (
          <section className="calendar-panel">
            <Calendar plan={plan} />
          </section>
        )}
      </main>
    </div>
  );
}