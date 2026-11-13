import { STATUSES, label } from "../utils/format";

export default function OrderFilters({ status, setStatus, dateFrom, setDateFrom, dateTo, setDateTo, statuses = STATUSES }) {
  return (
    <div className="filters">
      <label>
        Status
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">All</option>
          {statuses.map((item) => (
            <option key={item} value={item}>
              {label(item)}
            </option>
          ))}
        </select>
      </label>
      <label>
        From
        <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
      </label>
      <label>
        To
        <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
      </label>
    </div>
  );
}
