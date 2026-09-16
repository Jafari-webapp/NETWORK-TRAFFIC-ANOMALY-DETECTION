import React from 'react';

// Gemini replies in markdown (###, **bold**, * bullets). No markdown library
// is in this project, so this is a small, dependency-free renderer for just
// the handful of patterns Gemini actually uses — not a full markdown engine.
function renderInlineBold(text, keyPrefix) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) =>
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>
      : <React.Fragment key={`${keyPrefix}-${i}`}>{part}</React.Fragment>
  );
}

export default function MarkdownLite({ text }) {
  const lines = (text || '').split('\n');
  const blocks = [];
  let listItems = [];

  const flushList = (key) => {
    if (listItems.length) {
      blocks.push(
        <ul key={`ul-${key}`} className="list-disc pl-4 space-y-0.5 my-1">
          {listItems}
        </ul>
      );
      listItems = [];
    }
  };

  lines.forEach((line, i) => {
    const heading = line.match(/^(#{2,4})\s+(.*)/);
    const bullet = line.match(/^\s*[*-]\s+(.*)/);
    if (heading) {
      flushList(i);
      const size = heading[1].length === 2 ? 'text-base' : 'text-sm';
      blocks.push(
        <p key={i} className={`${size} font-bold mt-2 mb-1 first:mt-0`}>
          {renderInlineBold(heading[2], i)}
        </p>
      );
    } else if (bullet) {
      listItems.push(<li key={i}>{renderInlineBold(bullet[1], i)}</li>);
    } else if (line.trim() === '') {
      flushList(i);
    } else {
      flushList(i);
      blocks.push(<p key={i} className="my-1 first:mt-0">{renderInlineBold(line, i)}</p>);
    }
  });
  flushList('end');

  return <div>{blocks}</div>;
}
