import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";

export default function Chat({ messages, loading, phase, onSend }) {
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function handleSubmit(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    onSend(text);
  }

  function getLoadingMessage() {
    if (phase === "adjustment") return "Updating your calendar";
    if (phase === "plan") return "Building your plan";
    return "Thinking";
  }

  const lastMessage = messages[messages.length - 1];
  const showQuickReplies =
    !loading &&
    messages.length > 0 &&
    lastMessage?.role === "assistant" &&
    lastMessage?.content?.includes("(a)");

  return (
    <div className="chat">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            Say hi to get started — RepPath will walk you through setup.
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`bubble bubble-${m.role}`}>
            <span className="bubble-label">
              {m.role === "user" ? "You" : "RepPath"}
            </span>
            <ReactMarkdown>{m.content}</ReactMarkdown>
          </div>
        ))}

        {loading && (
          <div className="bubble bubble-assistant">
            <span className="bubble-label">RepPath</span>
            <p className="loading-dots">
              {getLoadingMessage()}
              <span>.</span><span>.</span><span>.</span>
            </p>
          </div>
        )}

        {showQuickReplies && (
          <div className="quick-replies">
            {["Build strength", "Build muscle", "Lose fat", "Build endurance"].map((option) => (
              <button
                key={option}
                className="quick-reply-btn"
                onClick={() => onSend(option)}
              >
                {option}
              </button>
            ))}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <form className="chat-input-row" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          disabled={loading}
          autoFocus
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}