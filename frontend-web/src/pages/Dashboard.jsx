import { useEffect, useState } from 'react';
import MapView from '../components/MapView';
import { fetchTrains } from '../services/api';

export default function Dashboard() {
	const [trains, setTrains] = useState([]);
	const [error, setError] = useState('');

	useEffect(() => {
		let active = true;
		fetchTrains()
			.then((data) => { if (active) setTrains(data); })
			.catch((reason) => { if (active) setError(reason.message); });
		return () => { active = false; };
	}, []);

	return (
		<main className="dashboard">
			<header><p>Station Master Command Center</p><h1>Railway ETA Dashboard</h1></header>
			{error && <p role="alert">Unable to load trains: {error}</p>}
			<MapView trains={trains} />
		</main>
	);
}
