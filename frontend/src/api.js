import axios from "axios";

const BASE = "http://localhost:8000/api";

export async function sendMessage(messages, plan = null) {
  const { data } = await axios.post(`${BASE}/chat`, { messages, plan });
  return data;
}