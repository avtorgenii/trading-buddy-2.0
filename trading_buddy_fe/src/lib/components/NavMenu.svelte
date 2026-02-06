<script lang="ts">
	import { Motion } from 'svelte-motion';
	import { API_BASE_URL } from '$lib/config';
	import { csrfToken } from '$lib/stores';
	import { showErrorToast, showSuccessToast } from '$lib/toasts';
	import { page } from '$app/stores';

	let user = $props();

	let screenWidth = $state(0);
	let mobileOpen = $state(false);
	let isMobile = $derived(screenWidth < 768);
	let left = $state(0);
	let width = $state(0);
	let opacity = $state(0);
	let activeItem = $state('');

	const baseNavs = [
		{ name: 'Trade', link: '/trade' },
		{ name: 'Positions', link: '/positions' },
		{ name: 'Stats', link: '/stats' },
		{ name: 'Journal', link: '/journal' },
		{ name: 'Settings', link: '/settings' }
	];

	let navs = $derived(user
		? [...baseNavs, { name: 'Log out', link: '/logout' }]
		: [...baseNavs, { name: 'Log in', link: '/login' }]);

	// Set active item based on current page
	$effect(() => {
		const currentPath = $page.url.pathname;
		const activeNav = navs.find(nav => nav.link === currentPath);
		if (activeNav) {
			activeItem = activeNav.name;
		}
	});

	async function handleLogout(event: MouseEvent) {
		event.preventDefault();

		const url = `${API_BASE_URL}/auth/logout/`;
		console.log(url);

		try {
			const response = await fetch(`${API_BASE_URL}/auth/logout/`, {
				method: 'POST',
				headers: {
					'X-CSRFToken': $csrfToken,
					'Content-Type': 'application/json'
				},
				credentials: 'include'
			});

			if (!response.ok) {
				throw new Error('Logout failed. Please try again.');
			}

			showSuccessToast('Successfully logged out!');
			window.location.href = '/login';

		} catch (error) {
			showErrorToast(error.message);
		}
	}

	function handleNavClick(itemName: string) {
		activeItem = itemName;
	}

	let positionMotion = (node: HTMLElement) => {
		let refNode = () => {
			let rect = node.getBoundingClientRect();
			left = node.offsetLeft;
			width = rect.width;
			opacity = 1;
		};
		node.addEventListener('mouseenter', refNode);
		return {};
	};

	// Set active background position when activeItem changes
	$effect(() => {
		if (activeItem) {
			// Find the active nav element and set background position
			const activeNavElement = document.querySelector(`[data-nav="${activeItem}"]`) as HTMLElement;
			if (activeNavElement) {
				left = activeNavElement.offsetLeft;
				width = activeNavElement.getBoundingClientRect().width;
				opacity = 1;
			}
		}
	});
</script>

<svelte:window bind:innerWidth={screenWidth} />

{#if isMobile}
	<div class="flex justify-between mb-8 border-b border-b-zinc-800 pb-4">
		<h1 class="text-3xl font-bold">Trading buddy 2.0</h1>
		<button
			class="border rounded px-2 py-1"
			onclick={() => (mobileOpen = !mobileOpen)}
		>
			&#9776;
		</button>
	</div>

	{#if mobileOpen}
		<div
			class="fixed inset-0 bg-black/50 z-40"
			onclick={() => mobileOpen = false}
			aria-hidden="true"
		></div>
	{/if}

	<div
		class="fixed top-0 right-0 h-full w-3/4 max-w-sm bg-zinc-900 transform transition-transform duration-300 z-50 {mobileOpen ? 'translate-x-0' : 'translate-x-full'}"
	>
		<div class="flex justify-end p-4">
			<button class="text-2xl" onclick={() => (mobileOpen = false)}>
				&times;
			</button>
		</div>
		<ul class="flex flex-col space-y-2 px-4">
			{#each navs as item}
				<li class="px-4 py-3 border border-zinc-700 rounded-2xl transition-colors duration-200 {item.name === activeItem ? 'bg-blue-700' : 'bg-zinc-900 hover:bg-blue-700'}">
					{#if item.name === 'Log out'}
						<button onclick={(e) => { handleNavClick(item.name); handleLogout(e); }} class="block w-full text-left">{item.name}</button>
					{:else}
						<a href={item.link} onclick={() => { handleNavClick(item.name); mobileOpen = false; }} class="block w-full">{item.name}</a>
					{/if}
				</li>
			{/each}
		</ul>
	</div>
{:else}
	<h1 class="text-4xl font-bold mb-3 text-center">Trading buddy 2.0</h1>
	<div class="py-10 w-full">
		<ul
			onmouseleave={() => {
        // Return to active item position if there is one
        if (activeItem) {
          const activeNavElement: HTMLElement | null = document.querySelector(`[data-nav="${activeItem}"]`);
          if (activeNavElement) {
            left = activeNavElement.offsetLeft;
            width = activeNavElement.getBoundingClientRect().width;
            opacity = 1;
          }
        } else {
          opacity = 0;
        }
      }}
			class="relative mx-auto flex w-fit rounded-full border-2 border-zinc-700 bg-zinc-900 p-1"
		>
			{#each navs as item, i}
				<li
					use:positionMotion
					data-nav={item.name}
					class="relative z-10 block px-3 py-2 text-white md:px-5 md:py-3 md:text-base transition-colors duration-200 {item.name === activeItem ? 'text-white' : 'text-gray-300'}"
				>
					{#if item.name === 'Log out'}
						<button class="text-lg cursor-pointer" onclick={(e) => { handleNavClick(item.name); handleLogout(e); }}>{item.name}</button>
					{:else}
						<a class="text-lg cursor-pointer" href={item.link} onclick={() => handleNavClick(item.name)}>{item.name}</a>
					{/if}
				</li>
			{/each}
			<Motion
				animate={{ left, width, opacity }}
				transition={{ type: "spring", stiffness: 400, damping: 30 }}
				let:motion
			>
				<li
					use:motion
					class="absolute z-0 h-7 rounded-full bg-blue-700 md:h-12"
				></li>
			</Motion>
		</ul>
	</div>
{/if}