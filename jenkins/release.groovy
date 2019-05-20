stage('Upload to github')
{
    node('ActiveClientWindowsBuilder') {
        withPythonEnv('python') {
            withCredentials([usernamePassword(credentialsId: 'github_friendsofgalaxy', usernameVariable: 'GITHUB_USERNAME', passwordVariable: 'GITHUB_TOKEN')]) {
                bat 'pip install -r jenkins/requirements.txt'
                version = bat(returnStdout: true, script: 'python setup.py --version').trim()
                bat "python jenkins/release.py ${version}"
            }
        }
    }
}
