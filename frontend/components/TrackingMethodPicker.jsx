const METHODS = [
  { value: "date_and_mileage", label: "By date & mileage", explainer: "Whichever comes first — ideal for services with time and distance limits." },
  { value: "date", label: "By date", explainer: "Get reminded after a certain amount of time has passed." },
  { value: "mileage", label: "By mileage", explainer: "Get reminded after driving a certain distance." },
];

export default function TrackingMethodPicker({ value, onChange, suggested, suggestionNote }) {
  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {METHODS.map((method) => {
          const selected = value === method.value;
          return (
            <button
              key={method.value}
              type="button"
              onClick={() => onChange(method.value)}
              className={`card block w-full text-left ${selected ? "ring-2 ring-gray-900" : ""}`}
            >
              {method.value === suggested && (
                <p className="mb-0.5 text-[12px] font-semibold text-amber-600">Suggested</p>
              )}
              <p className="font-semibold">{method.label}</p>
              <p className="mt-0.5 text-[13px] text-gray-500">{method.explainer}</p>
            </button>
          );
        })}
      </div>

      {suggestionNote && (
        <div className="rounded-xl bg-blue-50 p-3 text-[13px] text-blue-700">
          <p className="font-medium">Reminder suggestion</p>
          <p className="mt-0.5">{suggestionNote}</p>
        </div>
      )}
    </div>
  );
}
