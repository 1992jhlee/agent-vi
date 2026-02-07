import Link from "next/link";

interface ServiceCardProps {
  title: string;
  description: string;
  icon: string;
  highlights: string[];
  href: string;
  ctaText: string;
  requiresLogin?: boolean;
}

export default function ServiceCard({
  title,
  description,
  icon,
  highlights,
  href,
  ctaText,
  requiresLogin,
}: ServiceCardProps) {
  return (
    <div className="flex flex-col p-8 bg-white border-2 border-gray-200 rounded-xl hover:border-blue-400 hover:shadow-lg transition-all">
      {/* Icon */}
      <div className="text-5xl mb-4">{icon}</div>

      {/* Title & Description */}
      <h3 className="text-2xl font-bold mb-2 text-gray-900">{title}</h3>
      <p className="text-gray-600 mb-6">{description}</p>

      {/* Highlights */}
      <ul className="flex-1 space-y-2 mb-6">
        {highlights.map((highlight, index) => (
          <li key={index} className="flex items-start text-sm text-gray-700">
            <span className="text-blue-500 mr-2">✓</span>
            {highlight}
          </li>
        ))}
      </ul>

      {/* CTA Button */}
      <Link
        href={href}
        className="block text-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
      >
        {ctaText}
      </Link>

      {/* Login Required Badge */}
      {requiresLogin && (
        <p className="text-xs text-gray-400 text-center mt-3">
          로그인 필요
        </p>
      )}
    </div>
  );
}
