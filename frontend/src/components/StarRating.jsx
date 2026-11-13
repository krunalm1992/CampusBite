export default function StarRating({ value = 0, onChange }) {
  if (!onChange) {
    return (
      <span className="stars" aria-label={`${value} out of 5 stars`}>
        {[1, 2, 3, 4, 5].map((star) => (
          <span key={star} className={star <= value ? "star on" : "star"}>
            ★
          </span>
        ))}
      </span>
    );
  }
  return (
    <div className="stars" role="group" aria-label="Rating">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          className={star <= value ? "star on" : "star"}
          onClick={() => onChange(star)}
          aria-label={`${star} star${star > 1 ? "s" : ""}`}
        >
          ★
        </button>
      ))}
    </div>
  );
}
