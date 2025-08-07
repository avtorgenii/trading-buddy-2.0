export function getCookie(name) {
	let cookieValue = null;
	if (typeof document !== 'undefined' && document.cookie) {
		const cookies = document.cookie.split(';');
		// console.log(cookies);
		for (let i = 0; i < cookies.length; i++) {
			const cookie = cookies[i].trim();
			if (cookie.substring(0, name.length + 1) === (name + '=')) {
				cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
				break;
			}
		}
	}
	// console.log(cookieValue)
	return cookieValue;

}
