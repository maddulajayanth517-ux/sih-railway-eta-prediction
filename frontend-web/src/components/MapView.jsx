export default function MapView({ trains = [] }) {
	return (
		<section className="map-view" aria-label="Train positions">
			<h2>Live Train Positions</h2>
			<div className="map-grid">
				{trains.map((train) => (
					<article key={train.train_id} className="train-marker">
						<strong>{train.train_name}</strong>
						<span>{train.current_latitude.toFixed(4)}, {train.current_longitude.toFixed(4)}</span>
						<small>{train.current_speed} km/h</small>
					</article>
				))}
				{trains.length === 0 && <p>Waiting for telemetry...</p>}
			</div>
		</section>
	);
}
