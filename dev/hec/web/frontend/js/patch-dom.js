export function patchDOM(current, fresh, preserveIds = new Set()) {
  if (current.nodeType !== fresh.nodeType || current.nodeName !== fresh.nodeName) {
    current.replaceWith(fresh);
    return;
  }
  if (current.nodeType === Node.TEXT_NODE) {
    if (current.nodeValue !== fresh.nodeValue) current.nodeValue = fresh.nodeValue;
    return;
  }
  if (current.nodeType !== Node.ELEMENT_NODE) return;
  if (current.id && preserveIds.has(current.id)) return;
  for (const attribute of [...current.attributes]) {
    if (attribute.name === 'open' && current.tagName === 'DETAILS') continue;
    if (!fresh.hasAttribute(attribute.name)) current.removeAttribute(attribute.name);
  }
  for (const attribute of [...fresh.attributes]) {
    if (attribute.name === 'open' && current.tagName === 'DETAILS') continue;
    if (current.getAttribute(attribute.name) !== attribute.value) current.setAttribute(attribute.name,attribute.value);
  }
  const oldChildren = [...current.childNodes], newChildren = [...fresh.childNodes];
  for (let index=0;index<Math.max(oldChildren.length,newChildren.length);index++) {
    if (!newChildren[index]) oldChildren[index].remove();
    else if (!oldChildren[index]) current.append(newChildren[index]);
    else patchDOM(oldChildren[index],newChildren[index],preserveIds);
  }
}
