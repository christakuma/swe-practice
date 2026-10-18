// The status board: one page listing which services answered their last check.
const polka = require("polka");

const PORT = Number(process.env.PORT || 3000);
const services = [
  { name: "orders-api", up: true },
  { name: "payments", up: true },
  { name: "search", up: false },
];

function page() {
  const rows = services
    .map((s) => `<li>${s.up ? "UP  " : "DOWN"} ${s.name}</li>`)
    .join("\n");
  return `<!doctype html><title>Status</title><ul>\n${rows}\n</ul>\n`;
}

polka()
  .get("/", (req, res) => {
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.end(page());
  })
  .get("/healthz", (req, res) => res.end("ok\n"))
  .listen(PORT, () => console.log(`status board on :${PORT}`));
