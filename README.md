# Meet my AI Twin
A digital avatar that looks and sounds just like me. Users can prompt this clone to speak any appropriate message, to help spread awareness on the complexity and nuance of deepfake technology that exists today. 

## 🎬 Demo

<table align="center">
<tr>
<td align="center">

<!-- Inline playable video for GitHub and web preview -->
<video src="samples/Pink_Floyd.mp4" controls width="600" style="border-radius:16px;box-shadow:0px 0px 10px rgba(0,0,0,0.2);"></video>

<br>
<em>↑ Watch my AI twin speak in real time (1.8 s demo clip)</em>

</td>
</tr>
</table>

If your GitHub page doesn't render `<video>` previews (some mobile or dark-mode clients),  
you can also [▶️ watch the same demo here](samples/Pink_Floyd.mp4).

## Security
- User prompts are censored by AI before video synthesis to filter out inappropriate content
- Videos output on web app are non-downloadable
- Secret keys are obfuscated; samples are given in ```.env.example```

