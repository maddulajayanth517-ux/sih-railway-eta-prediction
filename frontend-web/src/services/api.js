const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
	const response = await fetch(`${API_BASE_URL}${path}`, {
		...options,
		headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
	});

	if (!response.ok) {
		throw new Error(`API request failed with status ${response.status}`);
	}

	return response.json();
}

export function fetchTrains() {
	return request('/api/trains');
}

export function fetchTrain(trainId) {
	return request(`/api/trains/${encodeURIComponent(trainId)}`);
}
