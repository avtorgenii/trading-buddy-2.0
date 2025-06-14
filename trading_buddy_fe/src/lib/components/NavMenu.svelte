<script lang="ts">
	import { Motion } from 'svelte-motion';
	import { API_BASE_URL } from '$lib/config';
	import { csrfToken } from '$lib/stores';
	import { showErrorToast, showSuccessToast } from '$lib/toasts';

	export let user = null;

	let screenWidth = 0;
	let mobileOpen = false;
	$: isMobile = screenWidth < 768;
	let left = 0;
	let width = 0;
	let opacity = 0;

	const baseNavs = [
		{ name: 'Trade', link: '/trade' },
		{ name: 'Positions', link: '/positions' },
		{ name: 'Stats', link: '/stats' },
		{ name: 'Settings', link: '/settings' }
	];

	$: navs = user
		? [...baseNavs, { name: 'Log out', link: '/logout' }]
		: [...baseNavs, { name: 'Log in', link: '/login' }];

	async function handleLogout(event: MouseEvent) {
		event.preventDefault();

		try {
			const response = await fetch(`${API_BASE_URL}/auth/logout/`, {
				method: 'POST',
				headers: {
					'X-CSRFToken': $csrfToken
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

	let positionMotion = (node: HTMLElement) => {
		let refNode = () => {
			let mint = node.getBoundingClientRect();
			left = node.offsetLeft;
			width = mint.width;
			opacity = 1;
		};
		node.addEventListener('mouseenter', refNode);
		return {};
	};
</script>

<svelte:window bind:innerWidth={screenWidth} />

{#if isMobile}
	<div class="flex justify-between mb-8 border-b border-b-zinc-800 pb-4 ">
		<h1 class="text-3xl font-bold">Trading buddy</h1>
		<button
			class="border rounded px-2 py-1"
			on:click={() => (mobileOpen = !mobileOpen)}
		>
			&#9776;
		</button>
	</div>

	{#if mobileOpen}
		<div
			class="fixed inset-0 bg-black/50 z-40"
			on:click={() => mobileOpen = false}
			aria-hidden="true"
		></div>
	{/if}

	<div
		class="fixed top-0 right-0 h-full w-3/4 max-w-sm bg-zinc-900 transform transition-transform duration-300 z-50 {mobileOpen ? 'translate-x-0' : 'translate-x-full'}"
	>
		<div class="flex justify-end p-4">
			<button class="text-2xl" on:click={() => (mobileOpen = false)}>
				&times;
			</button>
		</div>
		<ul class="flex flex-col space-y-2 px-4">
			{#each navs as item}
				<li class="px-4 py-3 border border-zinc-700 rounded-2xl bg-zinc-900 hover:bg-blue-700">
					{#if item.name === 'Log out'}
						<a href="#" on:click|preventDefault={handleLogout} class="block w-full">{item.name}</a>
					{:else}
						<a href={item.link} on:click={() => (mobileOpen = false)} class="block w-full">{item.name}</a>
					{/if}
				</li>
			{/each}
		</ul>
	</div>
{:else }
	<h1 class="text-4xl font-bold mb-3 text-center">Trading buddy</h1>
	<div class="py-10 w-full">
		<ul
			on:mouseleave={() => {
        opacity = 0;
      }}
			class="relative mx-auto flex w-fit rounded-full border-2 border-zinc-700 bg-zinc-900 p-1"
		>
			{#each navs as item, i}
				<li
					use:positionMotion
					class="relative z-10 block cursor-pointer px-3 py-2 text-white md:px-5 md:py-3 md:text-base"
				>
					{#if item.name === 'Log out'}
						<a href="#" class="text-lg" on:click|preventDefault={handleLogout}>{item.name}</a>
					{:else}
						<a class="text-lg" href={item.link}>{item.name}</a>
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