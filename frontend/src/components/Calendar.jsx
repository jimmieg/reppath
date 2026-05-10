const DAYS = [
    "Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"
  ];
  
  export default function Calendar({ plan }) {
    const dayMap = Object.fromEntries(
      (plan.schedule || []).map((d) => [d.day, d])
    );
  
    return (
      <div className="calendar">
        <div className="calendar-header">
          <h2>Your {plan.weeks}-Week Plan</h2>
          <p className="calendar-meta">
            {plan.goal?.replace("_", " ")} · {plan.days_per_week} days/week ·{" "}
            {plan.experience_level}
          </p>
        </div>
  
        <div className="calendar-grid">
          {DAYS.map((day) => {
            const session = dayMap[day];
            return (
              <div
                key={day}
                className={`day-card ${session ? "day-card--active" : "day-card--rest"}`}
              >
                <div className="day-card-header">
                  <span className="day-name">{day.slice(0, 3)}</span>
                  {session && (
                    <span className="session-type">{session.session_type}</span>
                  )}
                </div>
  
                {session ? (
                  <ul className="exercise-list">
                    {session.exercises.map((ex) => (
                      <li key={ex.id} className="exercise-item">
                        <span className="exercise-name">{ex.name}</span>
                        <span className="exercise-detail">
                          {ex.sets} × {ex.reps}
                          {ex.load_guidance && ` · ${ex.load_guidance}`}
                        </span>
                        {ex.notes && (
                          <span className="exercise-notes">{ex.notes}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="rest-label">Rest</p>
                )}
  
                {session?.estimated_duration_minutes && (
                  <div className="day-footer">
                    ~{session.estimated_duration_minutes} min
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }