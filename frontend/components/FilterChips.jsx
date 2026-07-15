export default function FilterChips({ options, value, onChange }) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`chip flex-shrink-0 whitespace-nowrap px-3 py-1.5 ${
            value === option.value ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
