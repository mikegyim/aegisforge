output "cluster_name" {
  value = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.this.endpoint
}

output "cluster_oidc_url" {
  value = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

output "irsa_role_arn" {
  value = aws_iam_role.aegisforge_irsa.arn
}

output "ecr_repository_url" {
  value = aws_ecr_repository.aegisforge.repository_url
}

output "vpc_id" {
  value = aws_vpc.this.id
}
