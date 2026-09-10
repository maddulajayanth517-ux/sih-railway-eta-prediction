import { useEffect, useState } from "react";

const backendUrl = "http://localhost:8000";

function App() {
	const [health, setHealth] = useState("Checking backend...");

	useEffect(() => {
		fetch(`${backendUrl}/health`)
			.then((response) => response.json())
			.then((data) => setHealth(`Backend ${data.status}`))
			.catch(() => setHealth("Backend unavailable"));
	}, []);

	return (
		<main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 960, margin: "0 auto", padding: 32 }}>
			<p style={{ color: "#55718a", letterSpacing: "0.08em", textTransform: "uppercase" }}>Railway ETA</p>
			<h1>Live train dashboard</h1>
			<p>Monitor train movement and predicted arrival delays from the Railway ETA backend.</p>
			<section style={{ border: "1px solid #d7e1e8", borderRadius: 8, padding: 20, marginTop: 24 }}>
				<strong>{health}</strong>
				<p style={{ marginBottom: 0 }}>Backend API: {backendUrl}</p>
			</section>
		</main>
	);
}

export default App;
