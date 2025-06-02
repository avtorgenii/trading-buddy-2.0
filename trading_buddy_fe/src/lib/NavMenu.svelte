<script lang="ts">
	import { Motion } from 'svelte-motion';

	let screenWidth = 0;
	let mobileOpen = false;
	$: isMobile = screenWidth < 768;
	let left = 0;
	let width = 0;
	let opacity = 0;
	let ref: any;
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
			destroy() {
				node.removeEventListener('mouseenter', refNode);
			}
		};
	};
</script>

<svelte:window bind:innerWidth={screenWidth} />

{#if isMobile}
	<div class="flex justify-end ">
	<button class="border-1 rounded-md px-1.5 py-0.5 "
		on:click={() => (mobileOpen = !mobileOpen)}>
		&#9776; <!-- TODO: Replace icon -->
	</button>
	</div>

	<div class="mb-4 mt-2 overflow-hidden transition-[max-height] duration-300 ease-in-out
    {mobileOpen ? 'max-h-[300px]' : 'max-h-0'}">
	{#if mobileOpen}
		<ul class="flex flex-col  ">
			{#each navs as item}
				<li
					class="px-4 py-3 border border-zinc-700 rounded-2xl bg-zinc-900">
					<a href={item.link}>{item.name}</a>
				</li>
			{/each}
		</ul>
	{/if}
	</div>
{:else }
	<div class="py-10 w-full">
		<ul
			on:mouseleave={() => {
        width = width;
        left = left;
        opacity = 0;
      }}
			class="relative mx-auto flex w-fit rounded-full border-2 border-zinc-700 bg-zinc-900 p-1"
		>
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