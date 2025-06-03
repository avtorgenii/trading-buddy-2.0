<script lang="ts">
	import { Motion } from 'svelte-motion';

	let screenWidth = 0;
	let mobileOpen = false;
	$: isMobile = screenWidth < 768;
	let left = 0;
	let width = 0;
	let opacity = 0;

	let navs = [
		{
			name: 'Home',
			link: '/'
		},
		{
			name: 'Trade',
			link: '/'
		},
		{
			name: 'Positions',
			link: '/'
		},
		{
			name: 'Stats',
			link: '/'
		},
		{
			name: 'Settings',
			link: '/'
		},
		{
			name: 'Log out',
			link: '/learnings'
		}
	];
	let positionMotion = (node: HTMLElement) => {
		let refNode = () => {
			let mint = node.getBoundingClientRect();
			left = node.offsetLeft;
			width = mint.width;
			opacity = 1;
		};
		node.addEventListener('mouseenter', refNode);
		return {
		};
	};
</script>

<svelte:window bind:innerWidth={screenWidth} />

{#if isMobile}
	<div class="flex justify-between mb-10 border-b border-b-zinc-800 pb-4 ">
		<h1 class="text-3xl font-bold">Trading buddy</h1>
		<button
			class="border rounded px-2 py-1"
			on:click={() => (mobileOpen = !mobileOpen)}
		>
			&#9776;
		</button>
	</div>

	<div
		class="fixed top-0 right-0 h-full w-3/4 bg-zinc-900 transform transition-transform duration-300 z-50 {mobileOpen ? 'translate-x-0' : 'translate-x-full'}"
	>
		<div class="flex justify-end p-4">
			<button class="text-2xl" on:click={() => (mobileOpen = false)}>
				&times;
			</button>
		</div>
		<ul class="flex flex-col space-y-2 px-4">
			{#each navs as item}
				<li class="px-4 py-3 border border-zinc-700 rounded-2xl bg-zinc-900 hover:bg-blue-700">
					<a
						href={item.link}
						on:click={() => (mobileOpen = false)}
						class="block"
					>
						{item.name}
					</a>
				</li>
			{/each}
		</ul>
	</div>
{:else }
	<h1 class="text-4xl font-bold mb-10 text-center">Trading buddy</h1>
	<div class="py-10 w-full">
		<ul
			on:mouseleave={() => {
        width = width;
        left = left;
        opacity = 0;
      }}
			class="relative mx-auto flex w-fit rounded-full border-2 border-zinc-700 bg-zinc-900 p-1">
			{#each navs as item, i}
				<li
					use:positionMotion
					class="relative z-10 block cursor-pointer px-3 py-2    text-white  md:px-5 md:py-3 md:text-base"
				>
					<a class="text-lg" href={item.link}>{item.name}</a>
				</li>
			{/each}
			<Motion
				animate={{
          left: left,
          width: width,
          opacity: opacity,
        }}
				transition={{
          type: "spring",
          stiffness: 400,
          damping: 30,

        }}
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